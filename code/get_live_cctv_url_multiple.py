import requests
import json
import urllib3

# SSL 경고 메시지 끄기
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_cctv_list():
    # ------------------------------------------------------------------
    # [입력] API KEY
    # ------------------------------------------------------------------
    API_KEY = "c78d3ec633114e4085cc92e5fe27aaa8"
    
    # ------------------------------------------------------------------
    # [설정] 찾고 싶은 CCTV 목록 (정확한 이름 매칭을 위해 리스트로 관리)
    # ------------------------------------------------------------------
    TARGET_LIST = [
        "[경부선] 서초",
        "[경부선] 금곡교",
        "[경부선] 달래내2",
        "[경부선] 기흥",
        "[경부선] 신갈분기점",
        "[경부선] 판교3"
    ]

    # API 요청 설정
    url = "https://openapi.its.go.kr:9443/cctvInfo"
    
    params = {
        "apiKey": API_KEY,
        "type": "ex",        # 고속도로
        "cctvType": "1",     # 동영상
        "minX": "126.0",     # 전국 범위
        "maxX": "130.0",
        "minY": "34.0",
        "maxY": "38.0",
        "getType": "json"
    }

    print(f"🚀 [ITS API] 데이터 요청 중...")

    try:
        response = requests.get(url, params=params, timeout=10, verify=False)
        response.raise_for_status()
        data = response.json()
        
        # 데이터 구조 파싱
        cctv_data_list = []
        if "response" in data and "data" in data["response"]:
            cctv_data_list = data["response"]["data"]
        elif "data" in data:
            cctv_data_list = data["data"]
        else:
            cctv_data_list = data

        print(f"✅ 전체 CCTV 데이터 수신 완료 (총 {len(cctv_data_list)}개)")
        
        # 결과를 담을 리스트 초기화
        final_results = []

        # 전체 CCTV 데이터를 순회하며 타겟 찾기
        for item in cctv_data_list:
            cctv_name = item.get("cctvname") or item.get("cctvName") or ""
            cctv_url = item.get("cctvurl") or item.get("cctvUrl")
            
            # 이름과 URL이 유효한 경우에만 검사
            if cctv_name and cctv_url:
                # 우리가 찾는 목록에 포함되어 있는지 확인 (부분 일치 허용)
                # 예: API가 "[경부선] 서초(서울)"이라고 줘도 "[경부선] 서초"가 포함되어 있으면 찾음
                for target in TARGET_LIST:
                    if target in cctv_name:
                        if "신갈분기점2" in cctv_name:
                            continue  # '신갈분기점2'는 저장하지 않고 건너뜀
                        if "기흥휴게소" in cctv_name:
                            continue
                        if "기흥동탄" in cctv_name:
                            continue

                        cctv_info = {
                            "name": cctv_name,
                            "url": cctv_url,
                            "coord": (item.get('coordx'), item.get('coordy'))
                        }
                        final_results.append(cctv_info)
                        # 중복 추가 방지 (한 CCTV가 여러 타겟에 걸릴 일은 드물지만 안전장치)
                        break 

        # 결과 출력 및 반환
        print("\n" + "="*60)
        print(f"🎉 총 {len(final_results)}개의 타겟 CCTV를 찾았습니다.")
        print("="*60)
        
        for res in final_results:
            print(f"📍 {res['name']}")
            print(f"   🔗 {res['url']}")
            print("-" * 60)

        # 못 찾은 CCTV가 있는지 확인
        found_names = [res['name'] for res in final_results]
        for target in TARGET_LIST:
            # 타겟 이름이 포함된 결과가 하나도 없으면 경고
            if not any(target in found for found in found_names):
                print(f"⚠️ [주의] '{target}' 은(는) 목록에서 찾지 못했습니다.")

        return final_results

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        return []

if __name__ == "__main__":
    # 함수 실행 및 결과 리스트 받기
    cctv_urls = get_cctv_list()

    print(type(cctv_urls))
    print(len(cctv_urls))
    print(cctv_urls)

    
    # (예시) 반환받은 리스트 활용
    # print(f"반환된 리스트 크기: {len(cctv_urls)}")