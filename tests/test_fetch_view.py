import re
import mock
import aiohttp
from aiounfurl.parsers.oembed import providers_helpers
from aiounfurl.views import fetch_all


def _read_file(file_obj):
    return file_obj.read()


async def fake_page(request):
    file_path = request.rel_url.query.get('file_path')
    with open(file_path) as f:
        file_content = _read_file(f)
    return aiohttp.web.Response(text=file_content)


async def fake_oembed(request):
    return aiohttp.web.json_response({
        "version": "1.0",
        "type": "photo",
        "width": 240,
        "height": 160,
        "title": "ZB8T0193",
        "url": "http://farm4.static.flickr.com/3123/2341623661_7c99f48bbf_m.jpg",
        "author_name": "Bees",
        "author_url": "http://www.flickr.com/photos/bees/",
        "provider_name": "Flickr",
        "provider_url": "http://www.flickr.com/"})


async def test_fetch_all_meta_tags(loop, test_client, test_server, files_dir):
    app = aiohttp.web.Application(loop=loop)
    app.router.add_get('/', fake_page)

    server = await test_server(app)
    client = await test_client(server)

    file_path = str(files_dir / 'meta_tags.html')
    url = client.make_url('/').with_query({'file_path': file_path})
    result = await fetch_all(client.session, url, loop=loop)
    assert 'meta_tags' in result
    assert 'description' in result['meta_tags']
    assert result['meta_tags']['description'] == '150 words'


async def test_fetch_oembed_discovery(loop, test_client, test_server, files_dir):
    app = aiohttp.web.Application(loop=loop)
    app.router.add_get('/', fake_page)
    app.router.add_get('/oembed', fake_oembed)

    server = await test_server(app)
    client = await test_client(server)

    file_path = str(files_dir / 'oembed_json.html')
    url = client.make_url('/').with_query({'file_path': file_path})
    original_read_file = _read_file

    def read_file_func(f):
        content = original_read_file(f)
        href = 'href="{0}"'.format(str(client.make_url('/oembed')))
        return re.sub(r'href=\"(.*)\"', href, content)

    with mock.patch('test_fetch_view._read_file', new=read_file_func):
        result = await fetch_all(client.session, url, loop=loop)
    assert 'oembed' in result
    assert 'provider_name' in result['oembed']
    assert result['oembed']['provider_name'] == 'Flickr'


async def test_fetch_all_oembed(loop, test_client, test_server, files_dir):
    app = aiohttp.web.Application(loop=loop)
    app.router.add_get('/', fake_page)
    app.router.add_get('/oembed', fake_oembed)

    server = await test_server(app)
    client = await test_client(server)

    file_path = str(files_dir / 'og.html')
    url = client.make_url('/').with_query({'file_path': file_path})
    providers = providers_helpers.prepare_providers([{
        "provider_name": "TestProvider",
        "provider_url": "{0}://{1}/".format(url.scheme, url.host),
        "endpoints": [
            {
                "schemes": [
                    "{0}*".format(url)
                ],
                "url": str(client.make_url('/oembed')),
                "formats": [
                    "json"
                ]
            }
        ]
    }])
    result = await fetch_all(
        client.session, str(url), loop=loop, oembed_providers=providers)
    assert 'oembed' in result
    assert result['oembed']['provider_name'] == 'Flickr'