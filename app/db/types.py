from decimal import Decimal

from sqlalchemy import Numeric

Money = Numeric(38, 12, asdecimal=True)
Price = Numeric(20, 12, asdecimal=True)
Score = Numeric(8, 4, asdecimal=True)

ZERO = Decimal("0")

