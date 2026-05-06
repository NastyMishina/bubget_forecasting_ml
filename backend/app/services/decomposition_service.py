
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")          
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose

logger = logging.getLogger(__name__)


_COLORS = {
    "observed": "#2563EB",
    "trend":    "#16A34A",
    "seasonal": "#D97706",  
    "residual": "#DC2626",  
}


class TimeSeriesDecompositionService:
    """Сервис декомпозиции временных рядов.

    Разбивает каждый признак на компоненты:
        Observed  — исходный ряд
        Trend     — тренд (скользящая средняя)
        Seasonal  — сезонная составляющая
        Residual  — остатки (шум)

    Использует statsmodels.seasonal_decompose с аддитивной моделью.
    """

    def __init__(self, decomposition_dir: Optional[str] = None) -> None:
        if decomposition_dir is None:
            base = Path(__file__).resolve().parent.parent.parent
            decomposition_dir = str(base / "data" / "decomposition")
        self.decomposition_dir = Path(decomposition_dir)
        self.decomposition_dir.mkdir(parents=True, exist_ok=True)


    def decompose_series(
        self,
        series: pd.Series,
        period: int = 4,
        model: str = "additive",
    ) -> dict:
        """Разложить временной ряд на компоненты.

        Args:
            series: pandas Series с числовыми данными временного ряда.
            period: длина сезонного периода (4 = квартальный, 12 = месячный).
            model: тип разложения ('additive' или 'multiplicative').

        Returns:
            dict с ключами: observed, trend, seasonal, residual — все как np.ndarray.
            Дополнительно: 'method' ('seasonal_decompose' | 'simplified').
        """
        clean = series.dropna().reset_index(drop=True)
        n = len(clean)

        min_required = 2 * period

        if n < min_required:
            logger.warning(
                "decompose_series: недостаточно данных для '%s' "
                "(нужно >= %d, есть %d). Применяем упрощённую декомпозицию.",
                series.name,
                min_required,
                n,
            )
            return self._simplified_decomposition(clean, period)

        try:
            result = seasonal_decompose(
                clean,
                model=model,
                period=period,
                extrapolate_trend="freq",  
                                        )
            logger.info(
                "decompose_series: '%s' — seasonal_decompose, n=%d, period=%d",
                series.name,
                n,
                period,
            )
            return {
                "observed": result.observed.values,
                "trend":    result.trend.values,
                "seasonal": result.seasonal.values,
                "residual": result.resid.values,
                "method":   "seasonal_decompose",
                "n":        n,
            }
        except Exception as exc:
            logger.warning(
                "decompose_series: ошибка seasonal_decompose для '%s': %s. "
                "Fallback на упрощённую декомпозицию.",
                series.name,
                exc,
            )
            return self._simplified_decomposition(clean, period)

    def generate_decomposition_plot(
        self,
        decomposition: dict,
        feature_name: str,
        upload_id: int,
        index: Optional[pd.Index] = None,
    ) -> str:
        """Сгенерировать PNG с 4 подграфиками декомпозиции.

        Args:
            decomposition: результат decompose_series().
            feature_name: имя признака (используется в заголовке и имени файла).
            upload_id: ID загрузки (используется в имени файла).
            index: индекс для оси X (даты / числа). Если None — целые числа.

        Returns:
            Путь к сохранённому PNG-файлу.
        """
        components = ["observed", "trend", "seasonal", "residual"]
        labels = ["Observed", "Trend", "Seasonal", "Residual"]

        n = len(decomposition["observed"])
        x = np.arange(n) if index is None else np.asarray(index)[:n]

        fig, axes = plt.subplots(
            nrows=4,
            ncols=1,
            figsize=(12, 9),
            sharex=True,
        )
        fig.suptitle(
            f"Декомпозиция: {feature_name}",
            fontsize=13,
            fontweight="bold",
            y=1.01,
        )

        for ax, key, label in zip(axes, components, labels):
            values = decomposition[key]
        
            xp = x[: len(values)]
            color = _COLORS[key]

            ax.plot(xp, values, color=color, linewidth=1.4, label=label)
            ax.fill_between(xp, values, alpha=0.08, color=color)
            ax.set_ylabel(label, fontsize=9, labelpad=4)
            ax.tick_params(axis="both", labelsize=8)
            ax.grid(True, linestyle="--", alpha=0.4)
            ax.spines[["top", "right"]].set_visible(False)

            if key == "observed":
                method = decomposition.get("method", "")
                ax.set_title(
                    f"n={decomposition.get('n', n)}, метод: {method}",
                    fontsize=8,
                    loc="right",
                    color="gray",
                )

        axes[-1].set_xlabel("Период", fontsize=9)
        fig.tight_layout()

        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in feature_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"decomp_{timestamp}_upload{upload_id}_{safe_name}.png"
        filepath = self.decomposition_dir / filename

        fig.savefig(filepath, dpi=100, bbox_inches="tight")
        plt.close(fig)

        logger.info("generate_decomposition_plot: сохранён %s", filepath)
        return str(filepath)



    def decompose_raw_features(
        self,
        df: pd.DataFrame,
        upload_id: int,
        period: int = 4,
        model: str = "additive",
    ) -> dict:
        """Разложить все признаки из DataFrame

        Args:
            df: DataFrame с признаками (может содержать лаги и rolling).
            upload_id: ID загрузки.
            period: период для seasonal_decompose.
            model: модель разложения.

        Returns:
            dict:
                features_decomposed: int — количество успешно разложенных рядов
                plot_paths: dict[str, str] — {feature_name: path_to_png}
                errors: dict[str, str] — {feature_name: error_message}
        """
        service_cols = {"period", "region", "upload_id"}
        lag_suffixes = ("_lag", "_roll", "_diff")

        raw_cols = [
            c for c in df.columns
            if c not in service_cols
            and not any(c.endswith(sfx) or sfx in c for sfx in lag_suffixes)
            and pd.api.types.is_numeric_dtype(df[c])
        ]

        if not raw_cols:
            logger.warning(
                "decompose_raw_features: чистых числовых признаков не найдено в DataFrame"
            )
            return {"features_decomposed": 0, "plot_paths": {}, "errors": {}}

        logger.info(
            "decompose_raw_features: найдено %d чистых признаков: %s",
            len(raw_cols),
            raw_cols,
        )

        x_index = None
        if "period" in df.columns:
            try:
                x_index = pd.to_datetime(df["period"]).dt.strftime("%Y-%m").values
            except Exception:
                x_index = None

        plot_paths: dict[str, str] = {}
        errors: dict[str, str] = {}

        for col in raw_cols:
            try:
                series = df[col].copy()
                series.name = col

                decomp = self.decompose_series(series, period=period, model=model)
                path = self.generate_decomposition_plot(
                    decomposition=decomp,
                    feature_name=col,
                    upload_id=upload_id,
                    index=x_index,
                )
                plot_paths[col] = path

            except Exception as exc:
                logger.error(
                    "decompose_raw_features: ошибка для '%s': %s",
                    col,
                    exc,
                    exc_info=True,
                )
                errors[col] = str(exc)

        logger.info(
            "decompose_raw_features: успешно=%d, ошибок=%d",
            len(plot_paths),
            len(errors),
        )

        return {
            "features_decomposed": len(plot_paths),
            "plot_paths": plot_paths,
            "errors": errors,
        }


    @staticmethod
    def _simplified_decomposition(series: pd.Series, period: int) -> dict:
        """Упрощённая декомпозиция для коротких рядов.

        Trend   — скользящая средняя (window = min(period, n//2))
        Seasonal — zeros (нельзя оценить сезонность без достаточных данных)
        Residual — observed - trend
        """
        n = len(series)
        window = max(2, min(period, n // 2))

        observed = series.values.astype(float)
        trend = (
            pd.Series(observed)
            .rolling(window=window, min_periods=1, center=True)
            .mean()
            .values
        )
        seasonal = np.zeros(n)
        residual = observed - trend

        return {
            "observed": observed,
            "trend":    trend,
            "seasonal": seasonal,
            "residual": residual,
            "method":   "simplified",
            "n":        n,
        }
