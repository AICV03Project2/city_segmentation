import requests

# 현재 실행 중인 Cloudflare 주소 또는 로컬 주소
TARGET_URL = "http://localhost:8000/update_urls" 

# 테스트용 수동 URL (실제 작동하는 m3u8 주소를 1~2개만 넣어도 됩니다)
test_data = {
    "urls": {
        1: "https://cctvsec.ktict.co.kr:8082/mgmt025/mgmtcctv00000001D/playlist.m3u8?wmsAuthSign=c2VydmVyX3RpbWU9MS8yMS8yMDI2IDY6MzU6MTMgQU0maGFzaF92YWx1ZT1FbzRRZXhVZzJneTlFUUVLMUFEZ1hBPT0mdmFsaWRtaW51dGVzPTEyMCZpZD1tbHRtI250aWNsaXZlIzk5",
        2: "여기에_실제_CCTV_주소_입력"
    }
}

try:
    response = requests.post(TARGET_URL, json=test_data)
    print(f"상태 코드: {response.status_code}")
    print(f"응답 내용: {response.json()}")
except Exception as e:
    print(f"에러 발생: {e}")