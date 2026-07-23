from limits.storage import Storage


class UpstashRedisStorage(Storage):
    STORAGE_SCHEME = ["upstash"]

    def __init__(self, uri: str = None, **options):
        super().__init__(uri, **options)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from app.db.session import get_redis

            self._client = get_redis()
        return self._client

    def incr(self, name: str, expiry: int, value: int = 1, **kwargs) -> int:
        client = self.client
        if not client:
            return value

        try:
            pipeline = client.pipeline()
            pipeline.incrby(name, value)
            pipeline.expire(name, expiry)
            res = pipeline.exec()
            return int(res[0])
        except Exception as e:
            raise e

    def get(self, name: str) -> int:
        client = self.client
        if not client:
            return 0
        try:
            val = client.get(name)
            return int(val) if val else 0
        except Exception:
            return 0

    def get_expiry(self, name: str) -> int:
        client = self.client
        if not client:
            return 0
        try:
            ttl = client.ttl(name)
            return ttl if ttl > 0 else 0
        except Exception:
            return 0

    def check(self) -> bool:
        client = self.client
        if not client:
            return False
        try:
            return bool(client.ping())
        except Exception:
            return False

    def reset(self) -> int:
        return 0

    def clear(self, name: str) -> None:
        client = self.client
        if client:
            try:
                client.delete(name)
            except Exception:
                pass
