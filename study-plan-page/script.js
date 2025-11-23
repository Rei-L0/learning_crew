// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getFirestore, collection, addDoc, getDocs, getDoc, doc, orderBy, query, serverTimestamp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";
import { GEMINI_API_KEY } from "./api-keys.js";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyBtRdhwtGbka6fwM7BXtWrACuXsG01J5jY",
  authDomain: "learning-crew-25a5b.firebaseapp.com",
  projectId: "learning-crew-25a5b",
  storageBucket: "learning-crew-25a5b.firebasestorage.app",
  messagingSenderId: "142305064128",
  appId: "1:142305064128:web:a14a7a533f34c231746925",
  measurementId: "G-SWKVKPXYC4"
};

// Gemini API configuration
const GEMINI_API_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=${GEMINI_API_KEY}`;

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

document.addEventListener('DOMContentLoaded', () => {
    // Check which page we are on
    const path = window.location.pathname;
    const page = path.split("/").pop();

    if (page === 'study-plan.html') {
        initStudyPlanPage();
    } else if (page === 'result-report.html') {
        initResultReportPage();
    } else if (page === 'evaluation-results.html') {
        initEvaluationResultsPage();
    } else if (page === 'report-detail.html') {
        initReportDetailPage();
    }
});

function initStudyPlanPage() {
    const addMemberBtn = document.getElementById('add-member-btn');
    const teamMembersContainer = document.getElementById('team-members-container');

    if (addMemberBtn) {
        addMemberBtn.addEventListener('click', () => {
            const newRow = document.createElement('div');
            newRow.className = 'input-row';
            newRow.style.marginTop = '10px';
            newRow.innerHTML = `
                <input type="text" placeholder="반" class="small-input">
                <input type="text" placeholder="학번" class="medium-input">
                <input type="text" placeholder="이름" class="medium-input">
            `;
            const memberGroup = teamMembersContainer.querySelector('.team-member-group');
            memberGroup.appendChild(newRow);
        });
    }
    
    // Webex Toggle Logic
    const webexRadios = document.querySelectorAll('input[name="webex"]');
    const webexEmailContainer = document.getElementById('webex-email-container');
    const webexEmailInput = document.getElementById('webex-email');

    if (webexRadios.length > 0 && webexEmailContainer && webexEmailInput) {
        webexRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                if (e.target.value === 'apply') {
                    webexEmailContainer.style.display = 'block';
                    webexEmailInput.setAttribute('required', 'true');
                } else {
                    webexEmailContainer.style.display = 'none';
                    webexEmailInput.removeAttribute('required');
                    webexEmailInput.value = ''; // Clear value when hidden
                }
            });
        });
    }

    const form = document.getElementById('study-plan-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Collect form data
            const goal = document.getElementById('study-goal').value;
            const planTextarea = document.querySelector('textarea[placeholder*="활동계획"]');
            const plan = planTextarea ? planTextarea.value : '';
            const leaderName = document.getElementById('leader-name').value || "익명";
            const campusSelect = document.getElementById('campus-select');
            const campus = campusSelect ? campusSelect.options[campusSelect.selectedIndex].text : "서울캠퍼스";
            
            // Count team members
            const memberInputs = document.querySelectorAll('#team-members-container .input-row input[placeholder="이름"]');
            const memberCount = memberInputs.length + 1; // +1 for leader
            
            // Show loading message
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Gemini로 평가 중...';
            submitBtn.disabled = true;
            
            try {
                // Call Gemini API for evaluation
                const evaluation = await evaluateStudyPlan({
                    goal,
                    plan,
                    memberCount
                });

                // Save to Firestore
                await addDoc(collection(db, "study_plans"), {
                    title: goal,
                    author: leaderName,
                    campus: campus,
                    date: serverTimestamp(),
                    status: "채점완료",
                    evaluation: evaluation
                });
                
                alert(`계획서가 제출되고 채점이 완료되었습니다!\n점수: ${evaluation.score}점\n\n${evaluation.feedback}`);
                window.location.href = 'evaluation-results.html';
            } catch (e) {
                console.error("Error adding document: ", e);
                alert("제출 중 오류가 발생했습니다.");
            } finally {
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }
        });
    }
}

async function callGeminiAPI(prompt) {
    try {
        const response = await fetch(GEMINI_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                contents: [{
                    parts: [{
                        text: prompt
                    }]
                }]
            })
        });

        if (!response.ok) {
            throw new Error(`Gemini API error: ${response.status}`);
        }

        const data = await response.json();
        return data.candidates[0].content.parts[0].text;
    } catch (error) {
        console.error('Gemini API 호출 실패:', error);
        throw error;
    }
}

async function evaluateStudyPlan(formData) {
    const prompt = `다음 스터디 계획서를 평가해주세요. 100점 만점으로 점수를 매기고, 구체적인 피드백을 제공해주세요.

활동 목표: ${formData.goal}
활동 계획: ${formData.plan}
팀원 수: ${formData.memberCount}명

평가 기준:
1. 목표의 명확성과 구체성
2. 계획의 실현 가능성
3. 팀원들과의 협업 방안
4. 학습 내용의 깊이

다음 형식으로 응답해주세요:
점수: [숫자]
피드백: [구체적인 피드백]`;

    try {
        const response = await callGeminiAPI(prompt);
        
        // 응답 파싱
        const scoreMatch = response.match(/점수:\s*(\d+)/);
        const feedbackMatch = response.match(/피드백:\s*(.+)/s);
        
        return {
            score: scoreMatch ? parseInt(scoreMatch[1]) : 85,
            feedback: feedbackMatch ? feedbackMatch[1].trim() : response
        };
    } catch (error) {
        console.error('평가 중 오류 발생:', error);
        // 폴백: 기본 평가 반환
        return {
            score: 85,
            feedback: '평가 시스템에 일시적인 문제가 발생했습니다. 계획서가 제출되었습니다.'
        };
    }
}

async function evaluateStudyReport(formData) {
    const prompt = `다음 스터디 결과보고서를 평가해주세요. 100점 만점으로 점수를 매기고, 구체적인 피드백을 제공해주세요.

활동 목표: ${formData.goal}
활동 내용: ${formData.content}
활동 소감: ${formData.reflection}
팀원 수: ${formData.memberCount}명

평가 기준:
1. 목표 달성도
2. 활동 내용의 구체성과 충실도
3. 학습한 내용의 깊이
4. 성찰과 개선 방안

다음 형식으로 응답해주세요:
점수: [숫자]
피드백: [구체적인 피드백]`;

    try {
        const response = await callGeminiAPI(prompt);
        
        // 응답 파싱
        const scoreMatch = response.match(/점수:\s*(\d+)/);
        const feedbackMatch = response.match(/피드백:\s*(.+)/s);
        
        return {
            score: scoreMatch ? parseInt(scoreMatch[1]) : 85,
            feedback: feedbackMatch ? feedbackMatch[1].trim() : response
        };
    } catch (error) {
        console.error('평가 중 오류 발생:', error);
        // 폴백: 기본 평가 반환
        return {
            score: 85,
            feedback: '평가 시스템에 일시적인 문제가 발생했습니다. 보고서가 제출되었습니다.'
        };
    }
}

function initResultReportPage() {
    const addMemberBtn = document.getElementById('add-member-btn');
    const teamMembersContainer = document.getElementById('team-members-container');

    if (addMemberBtn) {
        addMemberBtn.addEventListener('click', () => {
            const newRow = document.createElement('div');
            newRow.className = 'input-row';
            newRow.style.marginTop = '10px';
            newRow.innerHTML = `
                <input type="text" placeholder="반" class="small-input">
                <input type="text" placeholder="학번" class="medium-input">
                <input type="text" placeholder="이름" class="medium-input">
            `;
            const memberGroup = teamMembersContainer.querySelector('.team-member-group');
            memberGroup.appendChild(newRow);
        });
    }

    const form = document.getElementById('study-report-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Collect form data
            const campusSelect = form.querySelector('select');
            const campus = campusSelect ? campusSelect.options[campusSelect.selectedIndex].text : "서울캠퍼스";
            
            const leaderInputs = form.querySelectorAll('.team-member-group:first-child .input-row input');
            const leaderName = leaderInputs[2] ? leaderInputs[2].value : "익명";
            
            const goal = form.querySelector('input[placeholder*="활동목표"]').value;
            const content = form.querySelector('textarea[placeholder*="활동 내용"]').value;
            const reflection = form.querySelector('textarea[placeholder*="활동 소감"]').value;
            
            // Count team members
            const memberInputs = document.querySelectorAll('#team-members-container .input-row input[placeholder="이름"]');
            const memberCount = memberInputs.length + 1; // +1 for leader
            
            // Show loading message
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Gemini로 평가 중...';
            submitBtn.disabled = true;
            
            try {
                // Call Gemini API for evaluation
                const evaluation = await evaluateStudyReport({
                    goal,
                    content,
                    reflection,
                    memberCount
                });

                // Save to Firestore
                await addDoc(collection(db, "study_reports"), {
                    title: goal,
                    author: leaderName,
                    campus: campus,
                    content: content,
                    reflection: reflection,
                    date: serverTimestamp(),
                    status: "채점완료",
                    evaluation: evaluation
                });
                
                alert(`결과보고서가 제출되고 채점이 완료되었습니다!\n점수: ${evaluation.score}점\n\n${evaluation.feedback}`);
                window.location.href = 'evaluation-results.html';
            } catch (e) {
                console.error("Error adding document: ", e);
                alert("제출 중 오류가 발생했습니다.");
            } finally {
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }
        });
    }
}

async function initEvaluationResultsPage() {
    const tableBody = document.querySelector('.results-table tbody');
    if (!tableBody) return;

    // Clear existing rows (if any static ones exist)
    tableBody.innerHTML = '<tr><td colspan="5">데이터를 불러오는 중...</td></tr>';

    try {
        const q = query(collection(db, "study_plans"), orderBy("date", "desc"));
        const querySnapshot = await getDocs(q);
        
        tableBody.innerHTML = ''; // Clear loading message

        let count = querySnapshot.size;
        querySnapshot.forEach((doc) => {
            const data = doc.data();
            const date = data.date ? new Date(data.date.toDate()).toLocaleDateString() : '날짜 없음';
            
            const row = document.createElement('tr');
            // Store doc ID for later retrieval
            row.dataset.docId = doc.id;
            row.innerHTML = `
                <td>${count--}</td>
                <td class="text-left">${data.title}</td>
                <td>${data.author}</td>
                <td>${data.campus}</td>
                <td>${date}</td>
            `;
            // Click handler to navigate to detail page
            row.addEventListener('click', () => {
                window.location.href = `report-detail.html?id=${doc.id}`;
            });
            tableBody.appendChild(row);
        });

        if (querySnapshot.empty) {
            tableBody.innerHTML = '<tr><td colspan="5">제출된 계획서가 없습니다.</td></tr>';
        }

    } catch (e) {
        console.error("Error getting documents: ", e);
        tableBody.innerHTML = '<tr><td colspan="5">데이터를 불러오는 데 실패했습니다.</td></tr>';
    }
}


// Modal close handler
document.addEventListener('click', (e) => {
    const modal = document.getElementById('detail-modal');
    if (!modal) return;
    if (e.target.classList.contains('modal-close') || e.target.id === 'detail-modal') {
        modal.style.display = 'none';
    }
});

// Initialize report detail page
async function initReportDetailPage() {
    const params = new URLSearchParams(window.location.search);
    const docId = params.get('id');
    const container = document.getElementById('detail-container');
    
    if (!docId) {
        if (container) {
            container.innerHTML = '<p>문서 ID가 제공되지 않았습니다.</p>';
        }
        console.error('No document ID provided in URL');
        return;
    }
    
    if (!container) return;
    
    try {
        const docRef = doc(db, 'study_plans', docId);
        const docSnap = await getDoc(docRef);
        
        if (!docSnap.exists()) {
            container.innerHTML = '<p>해당 계획서를 찾을 수 없습니다.</p>';
            return;
        }
        
        const data = docSnap.data();
        const date = data.date ? new Date(data.date.toDate()).toLocaleDateString() : '날짜 없음';
        
        container.innerHTML = `
            <h2>${data.title}</h2>
            <div style="margin-top: 20px;">
                <p><strong>작성자:</strong> ${data.author}</p>
                <p><strong>캠퍼스:</strong> ${data.campus}</p>
                <p><strong>제출일:</strong> ${date}</p>
                <p><strong>평가 점수:</strong> ${data.evaluation?.score ?? 'N/A'}점</p>
                <p><strong>피드백:</strong></p>
                <p style="white-space: pre-wrap; background-color: #f9f9f9; padding: 15px; border-left: 3px solid #4a90e2;">${data.evaluation?.feedback ?? '피드백이 없습니다.'}</p>
            </div>
        `;
    } catch (e) {
        console.error('Error loading report detail:', e);
        container.innerHTML = '<p>데이터를 불러오는 중 오류가 발생했습니다.</p>';
    }
}
