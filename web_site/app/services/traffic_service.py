import requests
import urllib3

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TrafficAnalysisService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://openapi.its.go.kr:9443/cctvInfo"
        self.channel_configs = {
            1: {"target_name": "[경부선] 서초"},
            2: {"target_name": "[경부선] 달래내2"},
            3: {"target_name": "[경부선] 금곡교"},            
            4: {"target_name": "[경부선] 판교3"},
            5: {"target_name": "[경부선] 신갈분기점"},
            6: {"target_name": "[경부선] 수원"},
        }

    def get_cctv_url(self, channel_id: int):
        config = self.channel_configs.get(channel_id)
        if not config: return None

        params = {
            "apiKey": self.api_key,
            "type": "ex", "cctvType": "1",
            "minX": "126.0", "maxX": "130.0",
            "minY": "34.0", "maxY": "38.0",
            "getType": "json"
        }

        try:
            response = requests.get(self.api_url, params=params, verify=False, timeout=5)
            data = response.json()
            cctv_list = data.get("response", {}).get("data", [])

            for item in cctv_list:
                name = item.get("cctvname") or item.get("cctvName") or ""
                if config["target_name"] in name:
                    return item.get("cctvurl") or item.get("cctvUrl")
        except Exception as e:
            print(f"❌ API 요청 오류 (채널 {channel_id}): {e}")
        return None