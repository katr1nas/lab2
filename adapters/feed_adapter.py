from typing import Tuple

import numpy as np

from adapters.third_party import ThirdPartyPriceFeed
from data.data_source import DataSource


class ThirdPartyFeedAdapter(DataSource):
    def __init__(self, feed: ThirdPartyPriceFeed) -> None:
        self._feed = feed

    @property
    def label(self) -> str:
        return f"feed-{self._feed.describe()}"

    def load(self) -> Tuple[np.ndarray, np.ndarray]:
        quotes = self._feed.fetch_quotes()
        y = np.log(np.array([q["close_a"] for q in quotes]))
        x = np.log(np.array([q["close_b"] for q in quotes]))
        return y, x
