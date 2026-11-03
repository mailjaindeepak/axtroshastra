"""Single source for the Mulank report price. No dependencies, so renderers and payment code share it."""
MULANK_PRICE_PAISE = 29900          # Rs 299, the only amount this product ever charges
MULANK_LIST_PRICE_PAISE = 49900     # Rs 499, shown struck through next to the real price; never charged
MULANK_CURRENCY = "INR"


def list_price_confirmed() -> bool:
    """The Rs 499 regular price is shown (struck through, with the saving) only after the owner has confirmed
    it is a genuine regular price (MULANK_LIST_PRICE_CONFIRMED=1). Until then only Rs 299 is shown."""
    import os
    return os.getenv("MULANK_LIST_PRICE_CONFIRMED", "") == "1"


def show_list_price() -> bool:
    return list_price_confirmed() and MULANK_LIST_PRICE_PAISE > MULANK_PRICE_PAISE
