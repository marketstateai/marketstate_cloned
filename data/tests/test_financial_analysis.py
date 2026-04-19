from marketstate.marketstate_data.src.valuation import FinancialAnalysis
import pytest

class Calc:
    def sum_func(self, a, b):
        return a + b

class TestCheckout():
    def test_functionality(self):
        calc = Calc()
        # Illegal chars and values
        assert calc.sum_func(1, 2) == 3