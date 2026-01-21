## 0. 팀 소개
📌 팀명 : 뚫어뻥 <br>
📌 팀원 : 강지윤, 권소윤, 김동하, 김무겸, 노성호

<table>
  <tr>
    <td align="center">
     <img width="160" height="1600" alt="image" src="https://github.com/user-attachments/assets/06858002-5441-4fd4-aeb9-63fe101c513e" /><br/>강지윤
    </td>
    <td align="center">
      <img width="140" height="140" alt="image" src="https://github.com/user-attachments/assets/3d31f135-d623-43a2-a71a-0c451feb322e" />
<br/>권소윤
    </td>
    <td align="center">
      <img width="160" height="160" alt="image" src="https://github.com/user-attachments/assets/c23f06c1-a63d-4ce2-acfd-92bc66416da4" /><br/>김동하
    </td>
    <td align="center">
     <img width="150" height="150" alt="image" src="https://github.com/user-attachments/assets/10e8e153-ba3e-44e9-ab14-86bb45f2336a" /><br/>김무겸
    </td>
    <td align="center">
     <img width="160" height="160" alt="image" src="https://github.com/user-attachments/assets/fd76d37e-fcc4-4eaa-a379-f4ace36afd92" />
<br/>노성호
    </td>
  </tr>
  <tr>
    <td align="center">
      <a href="https://github.com/jiyun-kang12"><img src="https://img.shields.io/badge/GitHub-jiyun--kang12-1F1F1F?logo=github" alt="강지윤 GitHub"/></a>
    </td>
    <td align="center">
      <a href="https://github.com/gksqkf0824-commits"><img src="https://img.shields.io/badge/GitHub-gksqkf0824--commits-1F1F1F?logo=github" alt="권소윤 GitHub"/></a>
    </td>
    <td align="center">
      <a href="https://github.com/Kimmdgh"><img src="https://img.shields.io/badge/GitHub-Kimmdgh-1F1F1F?logo=github" alt="김동하 GitHub"/></a>
    </td>
    <td align="center">
      <a href="https://github.com/m00k1m"><img src="https://img.shields.io/badge/GitHub-m00k1m-1F1F1F?logo=github" alt="김무겸 GitHub"/></a>
    </td>
    <td align="center">
      <a href="https://github.com/0Devilkitty0"><img src="https://img.shields.io/badge/GitHub-0Devilkitty0-1F1F1F?logo=github" alt="노성호 GitHub"/></a>
    </td>
</table>

## 1. 프로젝트 개요
### 1.1. 프로젝트 주제
> 고속도로 CCTV 영상의 Segmentation을 활용한 공간 점유율 기반 교통 혼잡도 분석

### 1.2. 프로젝트 배경
고속도로 교통 혼잡 분석은 주로 센서 기반 지표에 의존해 왔으나, 이미 구축된 CCTV 영상 데이터를 활용하면 추가 인프라 없이도 교통 상황을 분석함.<br> 이에 본 주제는 Segmentation을 통해 차량의 공간 점유율을 산출하고, 이를 기반으로 교통 혼잡도를 정량적으로 분석하고자 선정함.

### 1.3. 목표 및 기대효과
- 고속도로 CCTV 영상에 Segmentation을 적용해 차량의 공간 점유율을 산출하고 이를 통해 교통 혼잡도를 정량적으로 분석
- 기존 센서 기반 방식의 한계를 보완하고, CCTV 영상만으로도 직관적이고 활용 가능한 교통 혼잡도 분석이 가능함을 제시

## 2. 사용 Dataset & Model
### 2.1. Dataset
- **데이터셋 출처:** [AI-Hub 교통문제 해결을 위한 CCTV 고속도로 교통 영상]([https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=164](https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=164&utm_source=chatgpt.com))
- **데이터 규모**: 총 505시간 동영상 및 학습 데이터 50만 장 이미지 중 **수도권 영동선** 선정
- **학습 데이터 형태:** Segmentation 이미지 : 37595장  (Polygon)
- **차종분류:** car, truck 및 bus 3종<br>
  <img width="300" height="200" alt="image" src="https://github.com/user-attachments/assets/cde8213b-0050-43a7-9a63-1914c9e47376" />

  
### 2.2. Model
- 차량 객체 탐지 모델: YOLOv8s-seg
- 도로 객체 탐지 모델: SAM3
  
## 3. 모델 성능결과
### 3.1. 모델 비교
### 📊 YOLO 모델 비교 (v8s vs v11s vs v8m)

<table>
  <tr>
    <td align="center"><b>YOLOv8s-seg</b></td>
    <td align="center"><b>YOLOv11s-seg</b></td>
    <td align="center"><b>YOLOv8m-seg</b></td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/46e0fffe-633e-4b7e-9390-9365864d28ee" width="330" alt="v8s"></td>
    <td><img src="https://github.com/user-attachments/assets/2b056ef3-7621-4b0c-baa8-ae619750dbb7" width="330" alt="v11s"></td>
    <td><img src="https://github.com/user-attachments/assets/feab5646-5c98-432d-8d77-67bc6dac44e0" width="330" alt="v8m"></td>
  </tr>
</table>

## 4. 웹페이지 구현
--- 캡쳐 이미지 넣기 -----
