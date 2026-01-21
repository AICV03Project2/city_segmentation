import asyncio
import cv2
import httpx
from datetime import datetime

class TrafficBridgeService:
    def __init__(self, colab_url):
        self.colab_url = f"{colab_url.rstrip('/')}/predict"
        self.latest_results = {}
        self.caps = {}

    async def analyze_channel(self, channel_id, m3u8_url):
        # 1. VideoCapture 초기화 및 지연 방지 설정
        if channel_id not in self.caps or not self.caps[channel_id].isOpened():
            # 버퍼를 1로 설정해도 HLS 특성상 데이터가 쌓일 수 있습니다.
            cap = cv2.VideoCapture(m3u8_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.caps[channel_id] = cap

        cap = self.caps[channel_id]

        try:
            # 2. [핵심 수정] 버퍼 비우기 (Frame Skipping)
            # 쌓여 있는 과거 프레임들을 디코딩 없이 빠르게 건너뜁니다.
            # 5~10프레임 정도 건너뛰면 현재 시점의 실시간 프레임에 도달합니다.
            for _ in range(5):
                cap.grab()
            
            # 건너뛴 직후의 가장 최신 프레임 하나만 실제로 가져옵니다.
            success, frame = cap.retrieve()

            if not success:
                print(f"⚠️ [채널 {channel_id}] 스트림 읽기 실패. 연결 재설정 중...")
                cap.release()
                self.caps[channel_id] = cv2.VideoCapture(m3u8_url)
                return None

            # 3. 이미지 처리 및 압축 (전송 속도 최적화)
            # 640x360 해상도는 AI 분석에 충분하면서도 전송이 매우 빠릅니다.
            frame = cv2.resize(frame, (320, 180))
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            
            # 4. 코랩 전송
            async with httpx.AsyncClient(timeout=10.0) as client:
                files = {'file': ('frame.jpg', buffer.tobytes(), 'image/jpeg')}
                data = {'channel_id': str(channel_id)}
                
                response = await client.post(self.colab_url, files=files, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    # 실시간 갱신 데이터 저장
                    self.latest_results[channel_id] = {
                        "results": result.get('results', {"up": 0, "low": 0}),
                        "encoded_image": result.get('encoded_image', ""),
                        "timestamp": datetime.now().isoformat()
                    }
                    return self.latest_results[channel_id]
                else:
                    print(f"❌ [채널 {channel_id}] 코랩 응답 오류: {response.status_code}")
                
        except httpx.ConnectError:
            print(f"❌ [채널 {channel_id}] 코랩 연결 실패. Ngrok 주소를 확인하세요.")
        except Exception as e:
            print(f"❌ [채널 {channel_id}] 분석 중 예외 발생: {str(e)}")
            return None

    def get_latest_data(self, channel_id):
        return self.latest_results.get(channel_id)