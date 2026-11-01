const questions = [
  { key: 'name', title: '你的姓名是？', expected: '温洁' },
  { key: 'gender', title: '你的性别是？', expected: '女' },
  { key: 'myName', title: '我的名字是？', expected: '赵旭东' },
  { key: 'yourBirthday', title: '你的生日是？' },
  { key: 'favoriteSong', title: '你最喜欢的歌是？' },
  { key: 'travelCity', title: '你最想去旅游的城市是？' },
];
const totalSteps = questions.length + 2;
const key = 'confession-app-draft-v1';
// Each page load begins a new response, so a previous visitor cannot continue it.
localStorage.removeItem(key);
let draft = { step: 0, answers: {}, affection: 0, choice: '' };
const $ = (id) => document.getElementById(id);
const questionView = $('questionView'), affectionView = $('affectionView'), choiceView = $('choiceView'), completeView = $('completeView');

function save() { localStorage.setItem(key, JSON.stringify(draft)); }
function normalizeDate(value) {
  const parts = value.trim().replace(/[/.]/g, '-').split('-');
  return parts.length === 3 && parts.every(p => /^\d+$/.test(p)) ? `${parts[0].padStart(4, '0')}-${parts[1].padStart(2, '0')}-${parts[2].padStart(2, '0')}` : value.trim();
}
function show(view) {
  [questionView, affectionView, choiceView, completeView].forEach(v => v.classList.add('hidden'));
  view.classList.remove('hidden');
}
function renderQuestion() {
  const q = questions[draft.step];
  $('progress').textContent = `第 ${draft.step + 1} / ${totalSteps} 步`;
  $('questionHint').textContent = q.type === 'date' ? '日期格式为：xxxx-xx-x' : '认真回答每一个问题吧';
  $('questionTitle').textContent = q.title;
  $('answerInput').value = draft.answers[q.key] || '';
  $('answerError').textContent = '';
  show(questionView);
  $('answerInput').focus();
}
function render() {
  if (draft.done) { $('progress').textContent = '完成'; show(completeView); return; }
  if (draft.step < questions.length) return renderQuestion();
  if (draft.step === questions.length) {
    $('progress').textContent = `第 ${questions.length + 1} / ${totalSteps} 步`; $('affectionRange').value = draft.affection; $('scoreNumber').textContent = draft.affection; $('affectionError').textContent = ''; show(affectionView); return;
  }
  $('progress').textContent = `第 ${totalSteps} / ${totalSteps} 步`; document.querySelectorAll('.choice').forEach(b => b.classList.toggle('selected', b.dataset.choice === draft.choice)); $('choiceError').textContent = ''; show(choiceView);
}
$('nextButton').addEventListener('click', () => {
  const q = questions[draft.step], raw = $('answerInput').value.trim();
  const answer = q.type === 'date' ? normalizeDate(raw) : raw;
  if (!answer) { $('answerError').textContent = '请先填写答案。'; return; }
  if (q.expected && answer !== q.expected) { $('answerError').textContent = '答案不对，再想一想吧。'; return; }
  draft.answers[q.key] = raw; draft.step++; save(); render();
});
$('answerInput').addEventListener('keydown', e => { if (e.key === 'Enter') $('nextButton').click(); });
$('affectionRange').addEventListener('input', e => { draft.affection = Number(e.target.value); $('scoreNumber').textContent = draft.affection; save(); });
$('affectionButton').addEventListener('click', () => {
  if (draft.affection <= 50) { $('affectionError').textContent = '不中哦TAT'; return; }
  draft.step++; save(); render();
});
document.querySelectorAll('.choice').forEach(button => button.addEventListener('click', () => { draft.choice = button.dataset.choice; save(); render(); }));
$('choiceButton').addEventListener('click', async () => {
  if (!draft.choice) { $('choiceError').textContent = '请选择一个选项。'; return; }
  $('choiceButton').disabled = true; $('choiceButton').textContent = '正在发送…';
  try {
    const response = await fetch('/api/submit', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(draft) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message);
    draft.done = true; save(); render();
  } catch (error) {
    $('choiceError').textContent = error.message || '发送失败，请稍后重试。';
    $('choiceButton').disabled = false; $('choiceButton').textContent = '确认选择';
  }
});
render();

