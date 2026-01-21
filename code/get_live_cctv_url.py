import requests
import json

# api key 이용해서 가져오기

def get_cctv_final_api():
    # ------------------------------------------------------------------
    # [입력] 발급받으신 API KEY를 여기에 넣으세요
    # ------------------------------------------------------------------
    API_KEY = ""  # Moo님의 키 입력됨
    
    # API 요청 설정
    url = "https://openapi.its.go.kr:9443/cctvInfo"
    
    params = {
        "apiKey": API_KEY,
        "type": "ex",        # ex: 고속도로 (서초는 경부선이므로 ex)
        "cctvType": "1",     # 1: 동영상
        "minX": "126.0",     # 전국 범위 검색 (좌표)
        "maxX": "130.0",
        "minY": "34.0",
        "maxY": "38.0",
        "getType": "json"    # JSON 형식
    }

    print(f"🚀 [PC] ITS 정식 API로 데이터 요청 중...")

    try:
        # verify=False 옵션을 추가하여 SSL 인증서 문제로 인한 타임아웃 방지
        response = requests.get(url, params=params, timeout=10, verify=False)
        response.raise_for_status()

        data = response.json()
        
        # 데이터 구조 파싱
        cctv_list = []
        if "response" in data and "data" in data["response"]:
            cctv_list = data["response"]["data"]
        elif "data" in data:
            cctv_list = data["data"]
        else:
            cctv_list = data

        print(f"✅ 데이터 수신 성공! 총 {len(cctv_list)}개의 CCTV를 찾았습니다.")

        # '서초' 검색
        target_name = "서초"
        found = False
        
        for item in cctv_list:
            # CCTV 이름 필드 확인 (대소문자 구분 없이 처리)
            name = item.get("cctvname") or item.get("cctvName") or ""
            
            if target_name in name:
                print(f"\n🎉 [발견] {name}")
                print(f"   - 좌표: {item.get('coordx')}, {item.get('coordy')}")
                
                # 영상 URL
                cctv_url = item.get("cctvurl") or item.get("cctvUrl")
                
                if cctv_url:
                    print("\n" + "="*60)
                    print("★ [정식] 실시간 재생 주소 (VLC 플레이어 사용):")
                    print("="*60)
                    print(cctv_url)
                    print("="*60 + "\n")
                    found = True
                    # 하나만 찾고 멈춤 (여러 개 찾으려면 break 제거)
                    break
        
        if not found:
            print(f"❌ '{target_name}' CCTV를 목록에서 찾지 못했습니다.")
            # 혹시 type이 틀렸을 수도 있으니 힌트 출력
            print("참고: 목록에 없다면 type을 'its'(국도)로 바꿔보세요.")

    except requests.exceptions.ConnectTimeout:
        print("\n❌ [실패] 서버 연결 시간 초과!")
        print("해외 IP(VPN 등)를 사용 중이거나, 회사 보안망에서 9443 포트를 막았을 수 있습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        # SSL 경고 숨기기용 (필요시)
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if __name__ == "__main__":
    # SSL 경고 메시지 끄기
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    get_cctv_final_api()