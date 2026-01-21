import requests
import urllib3
import time

# 1. SSL 경고 무시 (보내주신 코드 반영)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TrafficAnalysisService:
    def __init__(self, api_key: str, colab_url: str):
        self.api_key = api_key
        self.api_url = "https://openapi.its.go.kr:9443/cctvInfo"
        self.colab_endpoint = f"{colab_url.rstrip('/')}/update_urls"
        
        # 사용자가 정의한 채널 설정
        self.channel_configs = {
            1: {"target_name": "[경부선] 서초"},
            2: {"target_name": "[경부선] 달래내2"},
            3: {"target_name": "[경부선] 금곡교"},            
            4: {"target_name": "[경부선] 판교3"},
            5: {"target_name": "[경부선] 신갈분기점"},
            6: {"target_name": "[경부선] 기흥"},
        }

    def get_all_mapped_urls(self):
        """보내주신 로직과 동일하게 전체 리스트를 가져와 키워드 매핑"""
        params = {
            "apiKey": self.api_key,
            "type": "ex", 
            "cctvType": "1",
            "minX": "126.0", "maxX": "130.0",
            "minY": "34.0", "maxY": "38.0",
            "getType": "json"
        }

        mapped_results = {}
        try:
            # verify=False로 SSL 체크 건너뜀 (보내주신 로직 반영)
            response = requests.get(self.api_url, params=params, verify=False, timeout=10)
            data = response.json()
            cctv_list = data.get("response", {}).get("data", [])

            print(f"📡 API로부터 {len(cctv_list)}개의 CCTV 데이터를 수집했습니다.")

            # 각 채널 설정 순회하며 검색
            for ch_id, config in self.channel_configs.items():
                target = config["target_name"]
                for item in cctv_list:
                    # 이름 필드(cctvname 또는 cctvName) 확인 로직 반영
                    name = item.get("cctvname") or item.get("cctvName") or ""
                    if target in name:
                        url = item.get("cctvurl") or item.get("cctvUrl")
                        if url:
                            mapped_results[ch_id] = url
                            print(f"✅ 채널 {ch_id} 매칭: {name}")
                            break
            
            return mapped_results

        except Exception as e:
            print(f"❌ API 요청 오류: {e}")
            return None

    def send_to_colab(self, urls: dict):
        """검색된 URL들을 코랩 FastAPI 서버로 전송"""
        if not urls:
            print("⚠️ 전송할 데이터가 없습니다.")
            return

        try:
            response = requests.post(self.colab_endpoint, json={"urls": urls}, timeout=10)
            if response.status_code == 200:
                print(f"🚀 [{time.strftime('%H:%M:%S')}] 코랩 전송 성공!")
            else:
                print(f"⚠️ 전송 실패 ({response.status_code}): {response.text}")
        except Exception as e:
            print(f"❌ 코랩 연결 실패: {e}")

# ==========================================
# 실행부
# ==========================================
if __name__ == "__main__":
    # 1. 정보 설정
    MY_API_KEY = "c78d3ec633114e4085cc92e5fe27aaa8"
    MY_COLAB_URL = " https://invisible-validity-height-scotia.trycloudflare.com" 

    # 2. 서비스 초기화
    service = TrafficAnalysisService(MY_API_KEY, MY_COLAB_URL)

    print("🚀 CCTV 주소 검색 및 전송 시작...")
    
    while True:
        # 주소 매핑 실행
        current_urls = service.get_all_mapped_urls()
        
        if current_urls:
            # 코랩으로 전송
            service.send_to_colab(current_urls)
        
        # 주소 만료 대비 1시간마다 반복
        print(f"\n😴 다음 갱신까지 1시간 대기합니다.")
        time.sleep(3600)