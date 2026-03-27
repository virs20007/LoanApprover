from pydantic import BaseModel, field_validator, model_validator
from typing import Literal


class InvestmentRequest(BaseModel):
    country: Literal["us", "canada", "india", "uk", "new zealand", "netherlands", "germany", "france", "australia"]
    age: int
    monthly_income: float
    monthly_expenses: float
    risk_level: Literal["Low", "Medium", "High"]
    financial_goal: Literal["Savings", "Retirement", "Investment", "Buying house"]

    @field_validator("age")
    @classmethod
    def age_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Age must be a positive integer")
        return v

    @field_validator("monthly_income")
    @classmethod
    def income_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Monthly income must be non-negative")
        return v

    @field_validator("monthly_expenses")
    @classmethod
    def expenses_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Monthly expenses must be non-negative")
        return v

    @model_validator(mode="after")
    def expenses_must_not_exceed_income(self) -> "InvestmentRequest":
        if self.monthly_expenses > self.monthly_income:
            raise ValueError("Monthly expenses cannot exceed monthly income")
        return self


class InvestmentResponse(BaseModel):
    allocation: dict[str, float]
    investment_amounts: dict[str, float]
    total_investable_amount: float
    currency_symbol: str
    expected_annual_return: float
    expected_annual_volatility: float
    sharpe_ratio: float
    country_products: dict[str, str]
    market_data_source: str
    ai_explanation: str = ""
    llm_source: str = "none"
