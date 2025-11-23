// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getFirestore, collection, addDoc, getDocs, orderBy, query, serverTimestamp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";

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

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

document.addEventListener('DOMContentLoaded', () => {
    // Check which page we are on
    const path = window.location.pathname;
    const page = path.split("/").pop();

    if (page === 'study-plan.html') {
        initStudyPlanPage();
    } else if (page === 'evaluation-results.html') {
        initEvaluationResultsPage();
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
            // Note: In a real app, we would collect all fields. For this demo, we'll grab key ones.
            const title = document.getElementById('study-goal').value;
            const author = document.getElementById('leader-name').value || "익명";
            const campusSelect = document.getElementById('campus-select');
            const campus = campusSelect ? campusSelect.options[campusSelect.selectedIndex].text : "서울캠퍼스";
            
            // Mock Gemini API Call
            const evaluation = await mockGeminiEvaluation(title);

            try {
                await addDoc(collection(db, "study_plans"), {
                    title: title,
                    author: author,
                    campus: campus,
                    date: serverTimestamp(), // Use server timestamp
                    status: "채점완료",
                    evaluation: evaluation
                });
                alert('계획서가 제출되고 채점이 완료되었습니다!');
                window.location.href = 'evaluation-results.html';
            } catch (e) {
                console.error("Error adding document: ", e);
                alert("제출 중 오류가 발생했습니다.");
            }
        });
    }
}

async function mockGeminiEvaluation(title) {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Return dummy data
    return {
        score: Math.floor(Math.random() * 20) + 80, // 80-99
        feedback: `"${title}"에 대한 계획이 구체적이고 실현 가능성이 높습니다. 팀원들과의 협업 방식을 조금 더 구체화하면 좋겠습니다.`
    };
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
            row.innerHTML = `
                <td>${count--}</td>
                <td class="text-left">${data.title}</td>
                <td>${data.author}</td>
                <td>${data.campus}</td>
                <td>${date}</td>
            `;
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
