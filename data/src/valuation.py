import sys
import argparse
import yfinance as yf
from abc import ABC, abstractmethod
import pandas as pd
from dataclasses import dataclass, field
from typing import Any, Dict
import numpy as np
from enum import Enum

class CompanyType(Enum):
    SLOW_GROWER = 1 
    STALWARTS = 2
    FAST_GROWER = 3
    CYCLICAL = 4
    TURNAROUNDS = 5
    ASSET_PLAYS = 6
    GROWTH_PLAY = 7 # Financial statements of limited use

class DataProcessor:
    def process(self, df: pd.DataFrame, max_cols: int | None = None) -> pd.DataFrame:
        if df is None or df.empty:
            return df

        df = df.apply(pd.to_numeric, errors="coerce")

        if max_cols:
            df = df.iloc[:, :max_cols]

        return df

class FinancialStatement(ABC):
    def __init__(self, ticker, max_cols=None):
        self.ticker = ticker
        self.obj = yf.Ticker(ticker)
        self.processor = DataProcessor()
        self.max_cols = max_cols

    @abstractmethod
    def _fetch_raw(self):
        pass

    def fetch(self):
        raw = self._fetch_raw()
        return self.processor.process(raw, max_cols=self.max_cols)


class IncomeStatementTrailing(FinancialStatement):
    def __init__(self, ticker):
        super().__init__(ticker, max_cols=1)

    def _fetch_raw(self):
        return self.obj.get_income_stmt(freq='trailing')


class IncomeStatementYearly(FinancialStatement):
    def __init__(self, ticker):
        super().__init__(ticker, max_cols=4)

    def _fetch_raw(self):
        return self.obj.get_income_stmt(freq='yearly')


@dataclass
class Score:
    name: str
    achieved: float
    maximum: float
    weight: float = 1.0
    inputs: Dict[str, Any] = field(default_factory=dict)

    @property
    def normalized(self):
        return self.achieved / self.maximum if self.maximum != 0 else 0

    @property
    def weighted(self):
        return self.normalized * self.weight

    @property
    def weighted_max(self):
        return 1 * self.weight


class FinancialAnalysis:
    def __init__(self, ticker):
        self.income_trailing = IncomeStatementTrailing(ticker).fetch()
        self.income_yearly = IncomeStatementYearly(ticker).fetch()

    def revenue_history(self) -> Score:
        ttm = self.income_trailing.loc["TotalRevenue"]
        yearly = self.income_yearly.loc["TotalRevenue"]

        revenue_series = pd.concat([yearly.sort_index(), ttm])
        df = revenue_series.to_frame(name="TotalRevenue")

        df["YoYPctChange"] = df["TotalRevenue"].pct_change() * 100
        df["RevSignScore"] = df["YoYPctChange"].apply(
            lambda x: 3 if x > 0 else (-3 if x < 0 else 0)
        )

        # Weights
        decay = 0.7
        n = len(df)
        weights = decay ** np.arange(n - 1, -1, -1)
        weights = weights / weights.max()
        df["Weight"] = weights

        # Achieved weighted score per row
        df["WeightedScore"] = df["RevSignScore"] * df["Weight"]

        # Maximum possible per row
        df["MaxScore"] = 3 * df["Weight"]

        # Cumulative sums
        df["CumulativeAchieved"] = df["WeightedScore"].cumsum()
        df["CumulativeMaximum"] = df["MaxScore"].cumsum()

        achieved = df["WeightedScore"].sum()
        maximum = df["MaxScore"].sum()

        return Score(
            name="revenue_history",
            achieved=achieved,
            maximum=maximum,
            weight=ANALYSIS_WEIGHTS.get("revenue_history", 2),
            inputs={"df": df.copy(), "decay": decay}
        )

    def profit_margin_history(self) -> Score:
        ttm = self.income_trailing.loc[["TotalRevenue", "GrossProfit"]]
        yearly = self.income_yearly.loc[["TotalRevenue", "GrossProfit"]]

        df = pd.concat([ttm, yearly], axis=1).T
        df["ProfitMargin"] = df["GrossProfit"] / df["TotalRevenue"]
        df = df.sort_index(ascending=True)[["ProfitMargin"]]
        
        def score_pm(pm):
            if pd.isna(pm):
                return 0
            return int((pm * 100) // 20) + 1

        df["Score"] = df["ProfitMargin"].apply(score_pm)

        weights = [1.0, 0.8, 0.6, 0.4, 0.2]
        df["Weight"] = weights

        # Achieved weighted score per row
        df["WeightedScore"] = df["Score"] * df["Weight"]

        # Maximum possible per row
        df["MaxScore"] = 5 * df["Weight"]

        # Cumulative sums
        df["CumulativeAchieved"] = df["WeightedScore"].cumsum()
        df["CumulativeMaximum"] = df["MaxScore"].cumsum()

        achieved = df["WeightedScore"].sum()
        maximum = df["MaxScore"].sum()

        return Score(
            name="profit_margin_history",
            achieved=achieved,
            maximum=maximum,
            weight=ANALYSIS_WEIGHTS.get("profit_margin_history", 2),
            inputs={"df": df.copy(), "weights": weights}
        )

    def run_all(self) -> Dict[str, Score]:
        results = {}

        for method_name in ANALYSIS_WEIGHTS.keys():
            method = getattr(self, method_name)
            score = method()
            results[method_name] = score

            print("\n" + "="*60)
            print(f"ANALYSIS: {method_name}")
            print("="*60)

            print(f"Normalized Score : {score.normalized:.4f}")
            print(f"Weight           : {score.weight}")
            print(f"Weighted Score   : {score.weighted:.4f}")

            print("\nDataFrame used for scoring:")
            print(score.inputs["df"])
            print("="*60 + "\n")

        return results


ANALYSIS_WEIGHTS = {
    "revenue_history": 2,
    "profit_margin_history": 3,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Input a ticker')
    parser.add_argument(
        '-t', 
        '--ticker', 
        type=str
        )

    parser.add_argument(
        '-c', 
        '--company-type', 
        required=True,
        type=lambda x: CompanyType[x.upper()],
        help="One of: " + ", ".join([c.name for c in CompanyType])
        )

    args = parser.parse_args()

    analysis = FinancialAnalysis(args.ticker)
    scores = analysis.run_all()

    total = sum(s.weighted for s in scores.values())
    print("FINAL TOTAL SCORE:", total)
