# 분석 자료와 웹 입력

현재 샘플은 모두 가상입니다. 양천구 지도 배경 위의 실제 위치로 이용하면 안 됩니다.

- sample_candidates.csv: 후보 좌표·수용 가정·안전 조건·검토 상태·출처
- sample_buildings.csv: 건물 좌표·가상 수요·단위·출처
- catalog_metadata.json: 권역·A/B 후보 조합·규칙·출처
- analysis_result.json: 위 파일의 분석 결과와 웹 초기 입력
- analysis_result.comparison.csv: A/B 비교표

```powershell
python scripts/analyze_locations.py
```

독립 프리뷰의 시연 스냅샷까지 갱신하려면 --preview-snapshot을 명시합니다. 실제 자료로 자동 덮어쓰지 않도록 별도 출력 파일을 권장합니다.

scripts/prepare_demo_data.py는 초기 가상 자료를 생성한 도구입니다. 실제 입력 자료를 이 스크립트로 덮어쓰지 마세요.

## 안전과 수요

안전 상태는 pass/fail/unknown이며 미확인·부적합·보류 후보는 배정하지 않습니다. 수요와 수용 기준 단위가 같아야 합니다. 가구 수를 무게로 간주하지 않습니다.

실제 자료에는 is_demo=0, source_id, checked_at을 적고 메타정보 출처 대장에 근거를 등록합니다. 실제 경계·좌표·보행·진입·정차를 확인해야 하며 과거 수거표는 현재 GPS 동선이 아닙니다.
