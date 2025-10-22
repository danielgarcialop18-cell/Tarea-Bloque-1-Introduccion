class BaseExtractor:
    def entrada(self, ticker: str, start: str | None = None, end: str | None = None):
        raise NotImplementedError("Implementa este método en tu extractor concreto.")
