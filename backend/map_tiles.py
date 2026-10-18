"""VWorld 영상/도로명 타일 연결. 인증키와 공급자 오류 원문은 브라우저에 보내지 않는다."""
import asyncio
import os
from typing import Literal
from urllib.parse import quote
from urllib.request import Request as URLRequest, urlopen

from fastapi import APIRouter, HTTPException, Path, Request, Response

router = APIRouter(prefix='/api/map')
_slots = asyncio.Semaphore(8)


def configuration():
    enabled = bool(os.getenv('VWORLD_API_KEY', '').strip())
    return {'imagery_available': enabled, 'provider': 'VWorld', 'max_native_zoom':19,
            'key_exposed':False, 'capture_date':None,
            'message':'영상 보기 연결 가능 · 촬영일 미확인' if enabled else '.env의 VWORLD_API_KEY 설정 후 웹을 다시 시작해 주세요.'}


@router.get('/config')
def map_configuration():
    return configuration()


def fetch_tile(key, layer, z, x, y, referer):
    extension='jpeg' if layer=='Satellite' else 'png'
    url=f'https://api.vworld.kr/req/wmts/1.0.0/{quote(key,safe="")}/{layer}/{z}/{y}/{x}.{extension}'
    request=URLRequest(url,headers={'Referer':referer,'User-Agent':'GreenZone educational web/0.7'})
    # 예외/본문에 인증 URL이 포함될 수 있으므로 공급자 오류를 그대로 반환·출력하지 않는다.
    try:
        with urlopen(request,timeout=10) as result:
            content=result.read(2_000_001)
        if len(content)>2_000_000:
            raise ValueError('tile size')
        if layer=='Satellite' and content.startswith(b'\xff\xd8\xff'):
            return content,'image/jpeg'
        if layer=='Hybrid' and content.startswith(b'\x89PNG\r\n\x1a\n'):
            return content,'image/png'
    except Exception:
        pass
    raise HTTPException(502,'영상 타일을 불러오지 못했습니다. VWorld 키의 WMTS/TMS 권한·등록 URL과 연결 상태를 확인해 주세요.') from None


@router.get('/tiles/{layer}/{z}/{x}/{y}')
async def tile(request: Request, layer: Literal['Satellite','Hybrid'],
               z: int = Path(ge=1,le=19), x: int = Path(ge=0), y: int = Path(ge=0)):
    if x>=2**z or y>=2**z:
        raise HTTPException(404,'지도 타일 범위를 벗어났습니다.')
    key=os.getenv('VWORLD_API_KEY','').strip()
    if not key:
        raise HTTPException(503,'영상지도 인증키 설정이 필요합니다.')
    referer=os.getenv('VWORLD_DOMAIN','').strip() or str(request.base_url)
    async with _slots:
        content,mime=await asyncio.to_thread(fetch_tile,key,layer,z,x,y,referer)
    return Response(content,media_type=mime,headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
