import os
import cv2
import asyncio
import numpy as np
import torch
import base64
import uvicorn
import nest_asyncio
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime
from ultralytics import YOLO

# =========================
# 1) 초기 설정 & 경로
# =========================
BASE_PATH = os.getcwd() 
YOLO_PT_PATH = "/content/drive/MyDrive/Colab_Notebooks/Segmentation_pro/model_save/best_v8m.pt"
MASK_BASE_PATH = "/content/drive/MyDrive/Colab_Notebooks/Segmentation_pro/road_mask"
# HTML 파일이 있는 절대 경로 (사용자 환경에 맞춰 고정)
FRONT_ABS_PATH = "/content/drive/MyDrive/Colab_Notebooks/Segmentation_pro/web_site/front"

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
USE_HALF = torch.cuda.is_available()

app = FastAPI()
nest_asyncio.apply()

# 전역 상태
cached_urls = {}       # {int: str} 형식으로 저장
latest_results = {}    # 분석 결과 저장

# =========================
# 2) 모델 & 마스크 로드
# =========================
print(f"⏳ 모델 로딩 중 ({DEVICE})...")
model = YOLO(YOLO_PT_PATH)
model.to(DEVICE)
print("✅ 모델 로드 완료")

def load_all_masks():
    loaded = {}
    if not os.path.exists(MASK_BASE_PATH):
        print(f"⚠️ 마스크 경로 없음: {MASK_BASE_PATH}")
        return loaded
    for i in range(1, 7):
        for direct in ['up', 'low']:
            m_path = f"{MASK_BASE_PATH}/{i}_{direct}.png"
            if os.path.exists(m_path):
                mask_img = cv2.imread(m_path, cv2.IMREAD_GRAYSCALE)
                if mask_img is not None:
                    loaded[f"{i}_{direct}"] = mask_img
    print(f"✅ ROI 마스크 {len(loaded)}개 로드 완료")
    return loaded

preloaded_masks = load_all_masks()

# =========================
# 3) 핵심 분석 로직
# =========================
async def analyze_stream(channel_id: int, url: str):
    """개별 채널 분석 루프"""
    cap = cv2.VideoCapture(url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    print(f"🟢 [채널 {channel_id}] 분석 시작 (URL: {url[:30]}...)")
    
    try:
        while channel_id in cached_urls:
            # 1. 프레임 스킵 (최신 프레임 확보)
            for _ in range(10): cap.grab()
            success, frame = cap.retrieve()
            if not success: 
                print(f"⚠️ [채널 {channel_id}] 프레임 읽기 실패. 재시도 중...")
                await asyncio.sleep(1)
                continue

            H, W = frame.shape[:2]

            # 2. YOLO 추론 (imgsz=320 최적화)
            res = model.predict(source=frame, conf=0.25, iou=0.6, imgsz=320,
                               device=DEVICE, half=USE_HALF, verbose=False)[0]

            # 3. 세그멘테이션 분석
            vehicle_union = np.zeros((H, W), dtype=bool)
            if res.masks is not None:
                masks = res.masks.data.detach().cpu().numpy()
                for m in masks:
                    m_resized = cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST)
                    vehicle_union |= (m_resized > 0.5)

            final_data = {}
            for direct in ['up', 'low']:
                key = f"{channel_id}_{direct}"
                mask_src = preloaded_masks.get(key)
                if mask_src is not None:
                    roi_mask = cv2.resize(mask_src, (W, H), interpolation=cv2.INTER_NEAREST)
                    roi_bool = (roi_mask > 127)
                    occ_raw = np.sum(vehicle_union & roi_bool) / (np.sum(roi_bool) + 1e-8)
                    
                    status = "Smooth"
                    if occ_raw > 0.6: status = "Heavy"
                    elif occ_raw > 0.3: status = "Moderate"
                    final_data[direct] = {"occupancy_rate": round(occ_raw * 100, 2), "status": status}

            # 4. 시각화 및 이미지 압축 최적화
            annotated_frame = res.plot(boxes=False, masks=True)
            display_frame = cv2.resize(annotated_frame, (480, 270)) 
            _, buffer = cv2.imencode('.jpg', display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 45])
            img_str = base64.b64encode(buffer).decode('utf-8')

            # 5. 결과 저장
            latest_results[channel_id] = {
                "channel_id": channel_id,
                "vehicle_total_count": len(res.boxes) if res.boxes is not None else 0,
                "results": final_data,
                "encoded_image": img_str,
                "timestamp": datetime.now().isoformat()
            }
            
            await asyncio.sleep(0.05) 
            
    finally:
        cap.release()
        print(f"🔴 [채널 {channel_id}] 분석 종료")

# =========================
# 4) API 엔드포인트
# =========================

class URLUpdate(BaseModel):
    urls: Dict[str, str]

@app.post("/update_urls")
async def update_urls(data: URLUpdate):
    """로컬 PC에서 보내는 CCTV 주소들을 업데이트하고 분석 태스크 시작"""
    global cached_urls
    incoming_urls = data.urls
    for cid_raw, url in incoming_urls.items():
        try:
            cid = int(cid_raw)
            if cid not in cached_urls or cached_urls[cid] != url:
                cached_urls[cid] = url
                asyncio.create_task(analyze_stream(cid, url))
        except ValueError:
            continue
    print(f"📡 주소 업데이트 완료: 현재 {len(cached_urls)}개 채널 분석 중")
    return {"status": "success", "active_channels": list(cached_urls.keys())}

@app.get("/api/v1/traffic/{channel_id}")
async def get_traffic_data(channel_id: int):
    """JS 대시보드에서 수치 데이터(혼잡도 등)를 가져가는 API"""
    data = latest_results.get(channel_id)
    if data is None:
        return JSONResponse(content={"error": "no data"}, status_code=503)
    # 이미지 데이터는 제외하고 수치 데이터만 전송 (네트워크 절약)
    output = data.copy()
    if "encoded_image" in output: del output["encoded_image"]
    return output

@app.get("/video_feed/{channel_id}")
async def video_feed(channel_id: int):
    """HTML <img> 태그에 실시간 영상을 스트리밍"""
    async def frame_generator():
        while True:
            data = latest_results.get(channel_id)
            if data and "encoded_image" in data:
                img_data = base64.b64decode(data["encoded_image"])
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + img_data + b'\r\n')
            await asyncio.sleep(0.1)
    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/")
async def read_index():
    """메인 대시보드 페이지 반환"""
    index_path = os.path.join(FRONT_ABS_PATH, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(content={"error": f"index.html을 찾을 수 없습니다. 경로: {index_path}"}, status_code=404)

# 정적 파일 마운트
if os.path.exists(FRONT_ABS_PATH):
    app.mount("/front", StaticFiles(directory=FRONT_ABS_PATH), name="front")

# =========================
# 5) 서버 시작 및 자동 실행
# =========================
@app.on_event("startup")
async def startup_event():
    print(f"🚀 [Startup] 시스템 준비 완료.")

if __name__ == "__main__":
    print("🚀 FastAPI 서버 시작 중...")
    uvicorn.run(app, host="0.0.0.0", port=8000)