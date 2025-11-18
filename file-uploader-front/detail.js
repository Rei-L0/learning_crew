document.addEventListener("DOMContentLoaded", async () => {
  const detailContainer = document.getElementById("detailContainer");
  const loadingDiv = document.getElementById("detailLoading");
  const BASE_URL = "http://127.0.0.1:8000";

  // 1. URL에서 ID 파라미터 추출
  const urlParams = new URLSearchParams(window.location.search);
  const resultId = urlParams.get("id");

  if (!resultId) {
    loadingDiv.textContent = "❌ ID가 지정되지 않았습니다.";
    loadingDiv.style.color = "red";
    return;
  }

  try {
    // 2. 서버에서 세부 데이터 요청
    const response = await fetch(`${BASE_URL}/results/${resultId}`);
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error("해당 ID의 결과를 찾을 수 없습니다.");
      }
      throw new Error(`서버 응답 오류: ${response.statusText}`);
    }

    const result = await response.json();

    // 3. renderResultHTML 함수 (script.js에서 로드됨)를 사용하여 HTML 생성
    // 서버가 "analysis_data" 키에 파싱된 객체를 반환한다고 가정
    if (typeof renderResultHTML === "function") {
      const detailHtml = renderResultHTML(
        result.analysis_data, // 파싱된 JSON 객체
        result.filename
      );

      // 로딩 메시지 제거 및 결과 삽입
      loadingDiv.remove();
      detailContainer.innerHTML = detailHtml;

      // (중요) detail.html에서는 토글 기능이 필요 없으므로 항상 펼쳐진 상태로 둡니다.
      // style.css에서 #detailContainer 규칙으로 이미 처리되었습니다.
    } else {
      throw new Error(
        "renderResultHTML 함수를 찾을 수 없습니다. (script.js 로드 확인)"
      );
    }
  } catch (error) {
    console.error("세부 내용 로드 실패:", error);
    if (loadingDiv) {
      loadingDiv.textContent = `❌ 세부 내용을 불러오는 데 실패했습니다: ${error.message}`;
      loadingDiv.style.color = "red";
    }
  }
});
