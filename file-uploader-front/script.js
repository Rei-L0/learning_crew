// 1. 필요한 DOM 요소들을 선택합니다.
const uploadForm = document.getElementById("uploadForm");
const planFileInput = document.getElementById("planFile");
const reportFileInput = document.getElementById("reportFile");
const statusDiv = document.getElementById("status");
const resultContainer = document.getElementById("resultContainer");

// (참고: 로컬에서 실행시 http://127.0.0.1:8000 로 변경)
const BASE_URL = "http://127.0.0.1:8000";
const UPLOAD_URL = `${BASE_URL}/upload-and-analyze`;

// ✨ (중요) 이 함수는 detail.js에서도 재사용됩니다.
function renderResultHTML(data, filename) {
  // data가 null이거나 undefined일 경우 빈 객체로 처리
  if (!data) {
    console.error("renderResultHTML: data가 비어있습니다.", filename);
    data = {
      rationale: {},
      scores_weighted: {},
      uncertainties: ["데이터 없음"],
      final_comment: "분석 데이터를 불러오는 데 실패했습니다.",
      total: 0,
      photo_count_detected: 0,
    };
  }

  // 항목별 한글 매핑
  const rationaleMap = {
    plan_specificity: "계획 구체성",
    plan_feasibility: "계획 실현성",
    plan_measurability: "계획 측정성",
    result_specificity_goal: "결과 구체성 (목표)",
    team_participation_diversity: "팀 참여도/다양성",
    evidence_strength: "증빙 강도",
  };

  // 항목별 세부 평가 (rationale) HTML 생성
  let rationaleHtml = "<ul>";
  if (data.rationale) {
    for (const key in data.rationale) {
      const label = rationaleMap[key] || key;
      const score = data.scores_weighted ? data.scores_weighted[key] : "N/A";
      const rationaleText = data.rationale[key];
      rationaleHtml += `
          <li>
              <strong>${label} ( ${score}점 )</strong>
              <p>${rationaleText}</p>
          </li>`;
    }
  }
  rationaleHtml += "</ul>";

  // 참고 사항 (uncertainties) HTML 생성
  let uncertaintiesHtml = "<ul>";
  if (data.uncertainties && data.uncertainties.length > 0) {
    data.uncertainties.forEach((item) => {
      uncertaintiesHtml += `<li>${item}</li>`;
    });
  } else {
    uncertaintiesHtml += "<li>없음</li>";
  }
  uncertaintiesHtml += "</ul>";

  // 최종 결과를 '헤더'와 '콘텐츠'로 분리된 HTML로 반환
  return `
        <div class="result-item-container"> 
            
            <h3 class="result-header">📊 분석 결과 (${filename})</h3>
            
            <div class="result-content">
                <div class="result-box">
                    <div class="result-item">
                        <strong>총점</strong>
                        <span>${data.total || 0} 점</span>
                    </div>
                    <div class="result-item">
                        <strong>감지된 사진 수</strong>
                        <span>${data.photo_count_detected || 0} 장</span>
                    </div>
                </div>

                <h4>항목별 세부 평가</h4>
                ${rationaleHtml}

                <h4>참고 사항</h4>
                ${uncertaintiesHtml}

                <h4>최종 코멘트</h4>
                <p>${data.final_comment || "코멘트 없음"}</p>
            </div>
        </div>
    `;
}

// 2. 폼 'submit' 이벤트 리스너 (uploadForm이 있는 페이지에서만 실행)
if (uploadForm) {
  uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const planFiles = planFileInput.files;
    const reportFiles = reportFileInput.files;
    if (planFiles.length === 0 || reportFiles.length === 0) {
      statusDiv.textContent =
        "적어도 하나 이상의 계획서와 결과보고서 파일을 선택해주세요.";
      return;
    }
    const formData = new FormData();
    for (const file of planFiles) {
      formData.append("plan_files", file);
    }
    for (const file of reportFiles) {
      formData.append("report_files", file);
    }

    statusDiv.textContent = `업로드 중... (총 ${
      planFiles.length + reportFiles.length
    }개 파일)`;
    resultContainer.innerHTML = "";

    try {
      const response = await fetch(UPLOAD_URL, {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const responseData = await response.json();
        console.log("서버 응답:", responseData);

        const summary = responseData.summary;
        statusDiv.textContent = `✅ 분석 완료: ${summary.matched_count}건 매칭 성공, ${summary.unmatched_plans.length}건 계획서 매칭실패, ${summary.unmatched_reports.length}건 보고서 매칭실패`;

        // 매칭 실패 파일 표시
        if (
          summary.unmatched_plans.length > 0 ||
          summary.unmatched_reports.length > 0
        ) {
          let unmatchedHtml =
            '<div class="result-item-container error active">'; // 항상 펼쳐진 에러
          unmatchedHtml +=
            '<h3 class="result-header">--- 매칭 실패 ---</h3><div class="result-content"><ul>';
          summary.unmatched_plans.forEach((name) => {
            unmatchedHtml += `<li>[계획서] ${name} (짝을 찾지 못함)</li>`;
          });
          summary.unmatched_reports.forEach((name) => {
            unmatchedHtml += `<li>[보고서] ${name} (짝을 찾지 못함)</li>`;
          });
          unmatchedHtml += "</ul></div></div>";
          resultContainer.innerHTML += unmatchedHtml;
        }

        // 9-3. 성공/실패 결과 순회
        responseData.results.forEach((result) => {
          if (result.status === "success") {
            try {
              // (클라이언트 사이드 파싱)
              const rawString = result.analysis_result;
              const startIndex = rawString.indexOf("{");
              const endIndex = rawString.lastIndexOf("}");
              if (
                startIndex === -1 ||
                endIndex === -1 ||
                endIndex < startIndex
              ) {
                throw new Error(
                  "응답에서 유효한 JSON 객체를 찾을 수 없습니다."
                );
              }
              const cleanedString = rawString.substring(
                startIndex,
                endIndex + 1
              );
              const data = JSON.parse(cleanedString);

              resultContainer.innerHTML += renderResultHTML(
                data,
                result.filename
              );
            } catch (parseError) {
              console.error(
                "JSON 파싱 오류:",
                parseError,
                result.analysis_result
              );
              resultContainer.innerHTML += `
                <div class="result-item-container error active">
                  <h3 class="result-header">❌ ${result.filename} 분석 실패 (JSON 파싱 오류)</h3>
                  <div class="result-content">
                    <p>${parseError.message}</p>
                    <p><strong>원본 응답:</strong> ${result.analysis_result}</p>
                  </div>
                </div>`;
            }
          } else {
            // API 처리 실패
            resultContainer.innerHTML += `
              <div class="result-item-container error active">
                <h3 class="result-header">❌ ${result.filename} 분석 실패</h3>
                <div class="result-content">
                  <p>${result.error}</p>
                </div>
              </div>`;
          }
        });
      } else {
        statusDiv.textContent = `❌ 업로드 실패: ${response.statusText}`;
      }
    } catch (error) {
      console.error("업로드 중 오류 발생:", error);
      statusDiv.textContent = `❌ 오류 발생: ${error.message}`;
    }
  });
}

// --- 결과 항목 클릭(토글) 이벤트 리스너 (resultContainer가 있는 페이지에서만) ---
if (resultContainer) {
  resultContainer.addEventListener("click", (event) => {
    // 1. 클릭된 요소가 'result-header'인지 확인
    const header = event.target.closest(".result-header");
    if (!header) {
      return;
    }

    // 2. 헤더의 부모 컨테이너를 찾음
    const container = header.closest(".result-item-container");
    if (!container) {
      return;
    }

    // 3. 'error' 클래스가 없는 항목만 토글
    if (!container.classList.contains("error")) {
      container.classList.toggle("active");
    }
  });
}
