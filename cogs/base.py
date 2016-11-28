from collections import namedtuple

RESPONSE = namedtuple('response', 'status data')

class BaseCog:
    def __init__(self, bot):
        self.bot = bot

    async def request(self, url, _type='json', *, timeout=10, method='GET', **kwargs):
        if _type not in ('json', 'read', 'text'):
            return
        if kwargs.get('data') and method == 'GET':
            method = 'POST'
        async with self.bot._http.request(method, url, timeout=timeout, **kwargs) as resp:
            try:
                data = await getattr(resp, _type)()
            except:
                return RESPONSE(resp.status, None)
            else:
                return RESPONSE(resp.status, data)
