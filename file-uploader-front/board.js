document.addEventListener("DOMContentLoaded", async () => {
  const boardContainer = document.getElementById("boardContainer");
  const loadingDiv = document.getElementById("boardLoading");
  const BASE_URL = "http://127.0.0.1:8000";

  try {
    const response = await fetch(`${BASE_URL}/results`);
    if (!response.ok) {
      throw new Error(`서버 응답 오류: ${response.statusText}`);
    }

    const results = await response.json();

    if (loadingDiv) {
      loadingDiv.remove(); // 로딩 메시지 제거
    }

    if (results.length === 0) {
      boardContainer.innerHTML = "<p>저장된 분석 결과가 없습니다.</p>";
      return;
    }

    // 목록 생성
    results.forEach((result) => {
      const itemLink = document.createElement("a");
      itemLink.href = `detail.html?id=${result.id}`;
      itemLink.className = "board-item";

      // 날짜 포맷팅 (간단하게)
      const date = new Date(result.created_at).toLocaleString("ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });

      itemLink.innerHTML = `
        <div class="board-item-info">
          <span class="board-item-filename">${result.filename}</span>
          <span class="board-item-date">${date}</span>
        </div>
        <span class="board-item-score">${result.total_score || "N/A"} 점</span>
      `;
      boardContainer.appendChild(itemLink);
    });
  } catch (error) {
    console.error("결과 목록 로드 실패:", error);
    if (loadingDiv) {
      loadingDiv.textContent = `❌ 결과 목록을 불러오는 데 실패했습니다: ${error.message}`;
      loadingDiv.style.color = "red";
    }
  }
});
