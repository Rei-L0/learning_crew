// 1. 필요한 DOM 요소들을 선택합니다.
const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const statusDiv = document.getElementById('status');
const resultContainer = document.getElementById('resultContainer'); // ✨ 결과 컨테이너 추가

const UPLOAD_URL = 'http://127.0.0.1:8000/upload-and-analyze';

// 2. 폼(form)에서 'submit' 이벤트가 발생했을 때 실행될 함수를 등록합니다.
uploadForm.addEventListener('submit', async (event) => {
    
    // ... (3, 4, 5, 6, 7번 항목은 기존과 동일) ...
    event.preventDefault(); 
    const file = fileInput.files[0];
    if (!file) {
        statusDiv.textContent = '업로드할 파일을 선택해주세요.';
        return;
    }
    const formData = new FormData();
    formData.append('myFile', file);

    // 8. 서버로 'fetch' API를 사용하여 데이터를 전송합니다.
    statusDiv.textContent = '업로드 중...';
    resultContainer.innerHTML = ''; // ✨ 이전 결과가 있다면 초기화

    try {
        const response = await fetch(UPLOAD_URL, {
            method: 'POST', 
            body: formData,   
        });

        // 9. 서버로부터 응답을 받습니다.
        if (response.ok) {
            // ========================================================
            // ✨ 여기가 핵심 수정 부분입니다.
            // ========================================================
            
            const result = await response.json(); // 서버가 보낸 {filename, analysis_result} 객체
            statusDiv.textContent = '✅ 업로드 성공!';
            console.log('서버 응답:', result);

            // 9-1. analysis_result는 JSON이 아닌 '문자열'이므로 파싱이 필요합니다.
            //      "```json\n{...}\n```" 형태의 문자열에서 JSON 부분만 추출합니다.
            const cleanedString = result.analysis_result
                .replace(/^```json\n/, '') // 시작하는 ```json 제거
                .replace(/\n```$/, '');    // 끝나는 ``` 제거
            
            // 9-2. 정리된 문자열을 실제 JSON 객체로 변환합니다.
            const data = JSON.parse(cleanedString);

            // 9-3. 항목별 한글 매핑
            const rationaleMap = {
                "plan_specificity": "계획 구체성",
                "plan_feasibility": "계획 실현성",
                "plan_measurability": "계획 측정성",
                "result_specificity_goal": "결과 구체성 (목표)",
                "team_participation_diversity": "팀 참여도/다양성",
                "evidence_strength": "증빙 강도"
            };

            // 9-4. '항목별 세부 평가' 목록 HTML 생성
            let rationaleHtml = '<ul>';
            for (const key in data.rationale) {
                const label = rationaleMap[key] || key; // 매핑된 한글 이름 또는 원래 key 이름
                rationaleHtml += `<li><strong>${label}:</strong> ${data.rationale[key]}</li>`;
            }
            rationaleHtml += '</ul>';

            // 9-5. '참고 사항' 목록 HTML 생성
            let uncertaintiesHtml = '<ul>';
            if (data.uncertainties && data.uncertainties.length > 0) {
                data.uncertainties.forEach(item => {
                    uncertaintiesHtml += `<li>${item}</li>`;
                });
            } else {
                uncertaintiesHtml += '<li>없음</li>';
            }
            uncertaintiesHtml += '</ul>';

            // 9-6. 최종 결과를 resultContainer에 삽입
            resultContainer.innerHTML = `
                <h3>📊 분석 결과 (${result.filename})</h3>
                
                <div class="result-box">
                    <div class="result-item">
                        <strong>총점</strong>
                        <span>${data.total} 점</span>
                    </div>
                    <div class="result-item">
                        <strong>감지된 사진 수</strong>
                        <span>${data.photo_count_detected} 장</span>
                    </div>
                </div>

                <h4>항목별 세부 평가</h4>
                ${rationaleHtml}

                <h4>참고 사항</h4>
                ${uncertaintiesHtml}

                <h4>최종 코멘트</h4>
                <p>${data.final_comment}</p>
            `;
            // ========================================================
            // ✨ 수정 끝
            // ========================================================

        } else {
            // 서버에서 오류 응답을 보냈을 때
            statusDiv.textContent = `❌ 업로드 실패: ${response.statusText}`;
        }
    } catch (error) {
        // 10. 네트워크 오류 등 예외 처리
        console.error('업로드 중 오류 발생:', error);
        statusDiv.textContent = `❌ 오류 발생: ${error.message}`;
    }
});