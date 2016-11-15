class BaseCog:
    async def request(self, url, _type='json', *, timeout=10, method='GET', **kwargs):
        if _type not in ('json', 'read', 'text'):
            return
        if kwargs.get('data') and method == 'GET':
            method = 'POST'
        async with self.bot._http.request(method, url, timeout=timeout, **kwargs) as resp:
            assert resp.status == 200
            return await getattr(resp, _type)()
