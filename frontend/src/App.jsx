import { useEffect, useState } from 'react'
import './App.css'

const steps = [
  ['profile', '认识自己', '经历与偏好'],
  ['job', '读懂岗位', '任务与门槛'],
  ['match', '判断是否适合', '方向与申请'],
]
const sourceOptions = [
  ['company_official', '企业官网'], ['school_channel', '学校渠道'],
  ['recruiting_platform', '招聘平台'], ['referral_repost', '内推或转发'], ['unknown', '来源不确定'],
]
const states = { saved: '已收藏', planned: '计划投递', applied: '已投递', interview: '面试中', offer: '收到录用', rejected: '未通过', withdrawn: '已撤回' }
const actions = { save_job_archetype: '保存岗位类型', not_recommended_now: '当前不建议申请', gather_information: '先补充信息', explore_before_applying: '先探索再决定', priority_apply: '优先考虑申请', stretch_apply: '可以尝试申请', worth_applying: '值得申请', low_priority: '低优先级' }
const directions = { priority_direction: '优先探索方向', worth_exploring: '值得探索', low_priority_direction: '低优先级方向', needs_more_experience: '需要更多体验' }

async function api(path, options = {}) {
  let response
  try {
    response = await fetch(`/api${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } })
  } catch {
    throw new Error('无法连接本机服务。请双击项目中的 start_local.command，保持启动窗口开启，然后刷新页面。')
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status >= 500 && !data.detail) throw new Error('本机后端没有响应。请运行 start_local.command 后刷新页面。')
    if (response.status === 503) throw new Error('本机尚未配置模型 API Key。已有结果仍可查看。')
    if (response.status === 502) throw new Error('模型这次没有给出可用结果。请稍后重试，或调整输入内容。')
    throw new Error(typeof data.detail === 'string' ? data.detail : '输入未通过检查，请核对内容后重试。')
  }
  return data
}

function remember(patch) {
  const current = JSON.parse(localStorage.getItem('career-desk-selection') || '{}')
  localStorage.setItem('career-desk-selection', JSON.stringify({ ...current, ...patch }))
}

function List({ items = [], empty = '尚未提供' }) {
  return items.length ? <ul className="plain-list">{items.map((item, i) => <li key={`${item}-${i}`}>{item}</li>)}</ul> : <p className="muted">{empty}</p>
}
function Field({ label, hint, children }) {
  return <label className="field"><span className="field-label">{label}</span>{children}{hint && <small>{hint}</small>}</label>
}
function Empty({ symbol, title, text }) {
  return <div className="empty-state"><span className="empty-symbol">{symbol}</span><h3>{title}</h3><p>{text}</p></div>
}

function ProfileReview({ data }) {
  const b = data.background || {}, a = data.availability_constraints || {}
  return <div className="review-content">
    <div className="review-heading"><h3>请核对这份画像</h3><p>有错时修改左侧描述并重新分析。特别注意经历、技能和不喜欢的任务。</p></div>
    <div className="fact-line"><span>背景</span><strong>{[b.school, b.college_or_major, b.degree].filter(Boolean).join(' · ') || '待确认'}</strong></div>
    <div className="fact-line"><span>实习时间</span><strong>{a.semester_internship_available === false ? '学期中不到岗' : '学期安排待确认'}；假期每周 {a.vacation_days_per_week_min ?? '?'}–{a.vacation_days_per_week_max ?? '?'} 天</strong></div>
    <section className="review-block"><h4>真实经历与成果</h4><List items={(data.experiences || []).map(x => `${x.title}：${(x.user_actions || []).join('；') || '具体行动待确认'}；成果 ${(x.deliverables || []).join('、') || '待确认'}`)} /></section>
    <section className="review-block"><h4>已提取的技能</h4><List items={(data.skills || []).map(x => `${x.skill_name}：${x.self_reported_level || '程度待确认'}`)} /></section>
    <section className="review-block"><h4>任务偏好</h4><List items={(data.task_preferences || []).map(x => `${x.task_name} · ${x.preference_level === 'untested' ? '尚未体验' : x.preference_level === 'strong_like' ? '很喜欢' : x.preference_level === 'dislike' ? '不喜欢' : '需核对'}`)} /></section>
    <section className="review-block"><h4>还需要你确认</h4><List items={data.profile_gaps?.user_confirmation_questions || []} /></section>
    <details className="evidence-details"><summary>查看画像引用的原文证据</summary><List items={(data.evidence_registry || []).map(x => x.source_text)} /></details>
  </div>
}

function JobReview({ data }) {
  const meta = data.job_meta || {}, c = data.basic_conditions || {}
  return <div className="review-content">
    <div className="review-heading"><h3>{meta.original_title || '岗位画像草稿'}</h3><p>{meta.company || '公司待确认'} · 来源尚未独立核验</p></div>
    <div className="fact-line"><span>实际职能</span><strong>{data.function_classification?.primary_function || '待确认'}</strong></div>
    <div className="fact-line"><span>地点与时长</span><strong>{c.locations?.join('、') || '地点未知'}；{c.duration_months?.minimum ? `至少 ${c.duration_months.minimum} 个月` : '时长未知'}</strong></div>
    <section className="review-block"><h4>主要会做什么</h4><List items={(data.task_clusters || []).map(x => x.cluster_name)} /></section>
    <section className="review-block"><h4>明确要求</h4><List items={[c.degree_requirements?.minimum_degree, ...(c.graduation_cohorts?.values || []), ...(data.capability_requirements || []).filter(x => x.requirement_strength === 'must').map(x => x.capability_name)].filter(Boolean)} /></section>
    <section className="review-block"><h4>岗位没有说清楚</h4><List items={data.job_uncertainties?.missing_fields || []} /></section>
    <section className="review-block"><h4>系统修正与核验提醒</h4><List items={data.job_uncertainties?.warnings || []} empty="暂时没有额外提醒" /></section>
    <details className="evidence-details"><summary>查看岗位引用的原文证据</summary><List items={(data.evidence_registry || []).map(x => x.source_text)} /></details>
  </div>
}

function MatchReview({ alignment, score, resumeAdvice }) {
  const text = alignment.user_facing_explanation || {}
  return <div className="review-content">
    <div className="review-heading"><h3>匹配结果</h3><p>{text.one_sentence_conclusion || '请结合下方证据判断。'}</p></div>
    <div className="verdict-grid">
      <div className="verdict direction"><span>职业方向</span><strong>{score.career_direction_summary ?? '—'}</strong><p>{directions[score.career_direction_label] || score.career_direction_label}</p></div>
      <div className="verdict action"><span>当前申请</span><strong>{actions[score.current_action_label] || score.current_action_label}</strong><p>{alignment.current_application_eligibility?.explanation}</p></div>
    </div>
    {score.career_direction_summary == null && <p className="notice">核心任务的偏好证据不足，暂不生成总分。先了解或体验这些任务会更有帮助。</p>}
    <section className="review-block"><h4>高度契合</h4><List items={text.highly_aligned_points || []} /></section>
    <section className="review-block"><h4>缺口与风险</h4><List items={[...(alignment.gap_summary?.evidence_gaps || []), ...(text.main_risks || [])]} /></section>
    <section className="review-block"><h4>申请前值得问</h4><List items={text.questions_before_application || []} /></section>
    <section className="review-block"><h4>简历可强调的真实经历</h4><List items={text.resume_focus_candidates || []} /></section>
    <section className="review-block"><h4>不能写进简历的内容</h4><List items={text.prohibited_resume_additions || []} /></section>
    {resumeAdvice && <section className="review-block resume-advice"><h4>基于已确认事实的表达草稿</h4><p className="muted">{resumeAdvice.notice}</p>{resumeAdvice.suggestions.map(item => <div className="resume-suggestion" key={item.experience_id}><strong>{item.title}</strong><p>{item.suggested_sentence}</p>{item.job_focus.length > 0 && <small>与岗位相关的强调方向：{item.job_focus.join('；')}。这些方向没有自动写进句子。</small>}<small>证据：{item.source_evidence_ids.join('、') || '待补充'}</small>{item.warnings.map(warning => <small key={warning}>{warning}</small>)}</div>)}{resumeAdvice.needs_more_information.length > 0 && <div className="resume-suggestion"><strong>需要补充事实的经历</strong><List items={resumeAdvice.needs_more_information.map(item => `${item.title}：${item.reason}`)} /></div>}</section>}
    <p className="footnote">分数表示方向证据摘要，不是录取概率。当前资格由行动建议单独表示。</p>
  </div>
}

function App() {
  const [step, setStep] = useState('profile')
  const [busy, setBusy] = useState(''), [error, setError] = useState(''), [message, setMessage] = useState('')
  const [profileInput, setProfileInput] = useState({ school: '', major: '', degree: '本科', graduationYear: '', city: '', resume: '', preferences: '', consent: false })
  const [jobInput, setJobInput] = useState({ jd: '', sourceType: 'company_official', sourceReference: '' })
  const [profileDraft, setProfileDraft] = useState(null), [profileChecked, setProfileChecked] = useState(false), [savedProfile, setSavedProfile] = useState(null)
  const [jobDraft, setJobDraft] = useState(null), [savedJob, setSavedJob] = useState(null)
  const [matchConsent, setMatchConsent] = useState(false), [matchDraft, setMatchDraft] = useState(null), [savedMatch, setSavedMatch] = useState(null)
  const [resumeAdvice, setResumeAdvice] = useState(null)
  const [applications, setApplications] = useState([])
  const [backendOnline, setBackendOnline] = useState(true)
  const [jobs, setJobs] = useState([]), [jobSearch, setJobSearch] = useState('')
  const [settingsOpen, setSettingsOpen] = useState(false), [keyInput, setKeyInput] = useState('')
  const [modelStatus, setModelStatus] = useState({ provider: 'deepseek', configured: false })

  useEffect(() => {
    const selected = JSON.parse(localStorage.getItem('career-desk-selection') || '{}')
    api('/health').then(() => setBackendOnline(true)).catch(() => setBackendOnline(false))
    Promise.all([
      selected.profileVersion ? api(`/profiles/${encodeURIComponent(selected.profileVersion)}`).catch(() => null) : null,
      selected.jobId ? api(`/jobs/${encodeURIComponent(selected.jobId)}`).catch(() => null) : null,
      selected.matchId ? api(`/matches/${encodeURIComponent(selected.matchId)}`).catch(() => null) : null,
      api('/applications').catch(() => []),
      api('/jobs').catch(() => []),
      api('/settings/model-status').catch(() => ({ provider: 'deepseek', configured: false })),
    ]).then(([profile, job, match, records, savedJobs, providerStatus]) => {
      if (profile) setSavedProfile(profile)
      if (job) setSavedJob(job)
      if (match) setSavedMatch(match)
      setApplications(records)
      setJobs(savedJobs)
      setModelStatus(providerStatus)
      if (profile && job) setStep('match')
      else if (profile) setStep('job')
    })
  }, [])

  useEffect(() => {
    const matchId = savedMatch?.alignment?.match_meta?.match_id
    if (!matchId) return
    api(`/matches/${encodeURIComponent(matchId)}/resume-advice`)
      .then(data => setResumeAdvice({ matchId, data }))
      .catch(() => setResumeAdvice({ matchId, data: null }))
  }, [savedMatch])

  async function run(name, work) {
    setBusy(name); setError(''); setMessage('')
    try { await work() } catch (problem) { setError(problem.message || '操作没有完成，请重试。') }
    finally { setBusy('') }
  }
  function editProfile(field, value) { setProfileInput(x => ({ ...x, [field]: value })); setProfileDraft(null); setProfileChecked(false) }
  function editJob(field, value) { setJobInput(x => ({ ...x, [field]: value })); setJobDraft(null) }

  function saveModelKey(event) {
    event.preventDefault()
    run('model-key', async () => {
      const result = await api('/settings/model-key', { method: 'POST', body: JSON.stringify({ api_key: keyInput }) })
      setModelStatus(result)
      setKeyInput('')
      setSettingsOpen(false)
      setMessage('DeepSeek Key 已在本次运行中设置。可开始生成分析草稿。')
    })
  }

  function clearModelKey() {
    run('clear-key', async () => {
      const result = await api('/settings/model-key', { method: 'DELETE' })
      setModelStatus(result)
      setKeyInput('')
      setMessage('本次运行中输入的 Key 已清除。')
    })
  }

  function selectSavedJob(jobId) {
    run('select-job', async () => {
      const selected = await api(`/jobs/${encodeURIComponent(jobId)}`)
      setSavedJob(selected)
      setJobDraft(null)
      setMatchDraft(null)
      setSavedMatch(null)
      remember({ jobId, matchId: null })
      setStep('match')
      setMessage('已选择岗位，可以开始匹配。')
    })
  }

  function analyzeProfile(event) {
    event.preventDefault()
    run('profile', async () => {
      const result = await api('/profiles/analyze', { method: 'POST', body: JSON.stringify({
        resume_text: profileInput.resume, preferences_text: profileInput.preferences,
        basic_info: { school: profileInput.school || null, major: profileInput.major || null, degree: profileInput.degree || null, graduation_year: profileInput.graduationYear ? Number(profileInput.graduationYear) : null, current_city: profileInput.city || null },
        consent_to_send_resume: profileInput.consent,
      }) })
      setProfileDraft(result.draft); setMessage('画像草稿已生成。请核对右侧内容。')
    })
  }
  function saveProfile() {
    if (!profileDraft || !profileChecked) return
    run('save-profile', async () => {
      const confirmed = structuredClone(profileDraft)
      confirmed.profile_meta.confirmation_status = 'confirmed'
      await api('/profiles', { method: 'POST', body: JSON.stringify(confirmed) })
      setSavedProfile(confirmed); remember({ profileVersion: confirmed.profile_meta.profile_version, matchId: null })
      setProfileDraft(null); setMatchDraft(null); setSavedMatch(null); setStep('job')
      setMessage('画像已保存在本机。下一步解读岗位。')
    })
  }
  function analyzeJob(event) {
    event.preventDefault()
    run('job', async () => {
      const result = await api('/jobs/analyze', { method: 'POST', body: JSON.stringify({ jd_text: jobInput.jd, source_type: jobInput.sourceType, source_reference: jobInput.sourceReference || 'user_paste' }) })
      setJobDraft(result.draft); setMessage('岗位画像草稿已生成。请核对真实任务与申请门槛。')
    })
  }
  function saveJob() {
    if (!jobDraft) return
    run('save-job', async () => {
      await api('/jobs', { method: 'POST', body: JSON.stringify(jobDraft) })
      setSavedJob(jobDraft); remember({ jobId: jobDraft.job_meta.job_id, matchId: null })
      setJobs(current => [{ job_id: jobDraft.job_meta.job_id, company: jobDraft.job_meta.company, title: jobDraft.job_meta.original_title, location: (jobDraft.basic_conditions?.locations || []).join('、'), primary_function: jobDraft.function_classification?.primary_function }, ...current])
      setJobDraft(null); setMatchDraft(null); setSavedMatch(null); setStep('match')
      setMessage('岗位已保存在本机。现在可以分析匹配。')
    })
  }
  function analyzeMatch() {
    if (!savedProfile || !savedJob) return
    run('match', async () => {
      const result = await api('/matches/analyze', { method: 'POST', body: JSON.stringify({ profile_version: savedProfile.profile_meta.profile_version, job_id: savedJob.job_meta.job_id, consent_to_send_profile: matchConsent }) })
      setMatchDraft(result); setMessage('匹配分析已生成。请检查支持点、风险和当前申请资格。')
    })
  }
  function saveMatch() {
    if (!matchDraft) return
    run('save-match', async () => {
      await api('/matches', { method: 'POST', body: JSON.stringify(matchDraft.alignment) })
      setSavedMatch({ alignment: matchDraft.alignment, score: matchDraft.score })
      remember({ matchId: matchDraft.alignment.match_meta.match_id }); setMatchDraft(null)
      setMessage('匹配结果已保存在本机。')
    })
  }
  function saveApplication() {
    if (!savedJob) return
    run('application', async () => {
      const item = await api('/applications', { method: 'POST', body: JSON.stringify({ company: savedJob.job_meta.company || '公司待确认', role: savedJob.job_meta.original_title, job_id: savedJob.job_meta.job_id, match_id: savedMatch?.alignment?.match_meta?.match_id || null, status: 'saved' }) })
      setApplications(x => [item, ...x]); setMessage('已加入求职记录。')
    })
  }
  function updateApplication(id, status) {
    run(`application-${id}`, async () => {
      const previous = applications.find(item => item.application_id === id)
      const changes = { status, interviewed: !!previous?.interviewed || status === 'interview' || status === 'offer' }
      if (!previous?.applied_on && ['applied', 'interview', 'offer', 'rejected'].includes(status)) {
        const today = new Date()
        changes.applied_on = new Date(today.getTime() - today.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
      }
      const item = await api(`/applications/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(changes) })
      setApplications(x => x.map(old => old.application_id === id ? item : old)); setMessage('求职状态已更新。')
    })
  }
  function updateApplicationNotes(id, notes) {
    const previous = applications.find(item => item.application_id === id)
    if (previous?.notes === notes) return
    run(`notes-${id}`, async () => {
      const item = await api(`/applications/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify({ notes }) })
      setApplications(x => x.map(old => old.application_id === id ? item : old))
      setMessage('备注已保存。')
    })
  }

  const visibleProfile = profileDraft || savedProfile, visibleJob = jobDraft || savedJob, visibleMatch = matchDraft || savedMatch
  const filteredJobs = jobs.filter(job => `${job.company || ''} ${job.title || ''} ${job.location || ''} ${job.primary_function || ''}`.toLowerCase().includes(jobSearch.trim().toLowerCase()))
  return <div className="app-shell">
    <header className="site-header">
      <div className="header-inner">
        <div className="brand"><span className="brand-mark">径</span><div><strong>实习路径</strong><span>独立研究原型</span></div></div>
        <nav className="step-nav" aria-label="产品流程">{steps.map(([id, label, detail], i) => <button key={id} className={`step-link ${step === id ? 'active' : ''}`} disabled={(i === 1 && !savedProfile) || (i === 2 && (!savedProfile || !savedJob))} onClick={() => { setStep(id); setError(''); setMessage('') }}><span className="step-number">{i + 1}</span><span><strong>{label}</strong><small>{detail}</small></span>{((id === 'profile' && savedProfile) || (id === 'job' && savedJob) || (id === 'match' && savedMatch)) && <span className="step-done">✓</span>}</button>)}</nav>
        <div className="header-actions"><span className={`model-pill ${modelStatus.configured ? 'ready' : ''}`}>{modelStatus.configured ? '模型已设置' : '模型未设置'}</span><button className="settings-trigger" type="button" aria-expanded={settingsOpen} onClick={() => { setSettingsOpen(!settingsOpen); setKeyInput('') }}>模型设置</button></div>
      </div>
      {settingsOpen && <div className="settings-popover"><div className="settings-heading"><h2>模型连接</h2><button aria-label="关闭模型设置" type="button" onClick={() => { setSettingsOpen(false); setKeyInput('') }}>×</button></div><p>当前服务商：{modelStatus.provider === 'deepseek' ? 'DeepSeek' : 'OpenAI'}。Key 只保存在本机后端当前进程中，关闭服务后需要重新输入。</p>{modelStatus.provider === 'deepseek' ? <form onSubmit={saveModelKey}><Field label="DeepSeek API Key"><input type="password" autoComplete="off" spellCheck="false" value={keyInput} onChange={e => setKeyInput(e.target.value)} placeholder="在这里输入，不要发到聊天里" /></Field><button className="primary-button" type="submit" disabled={!!busy || keyInput.trim().length < 20}>{busy === 'model-key' ? '正在设置…' : '在本机设置 Key'}</button>{modelStatus.source === 'runtime' && <button type="button" className="text-button" onClick={clearModelKey}>清除本次输入</button>}</form> : <p>当前选择 OpenAI，请在启动后端的终端配置 OPENAI_API_KEY。</p>}</div>}
    </header>
    <main className="main-panel">
      <div className="topbar"><span>面向商科学生的岗位理解工作台 · 与学院职业指导互补</span><span className="step-count">{steps.findIndex(x => x[0] === step) + 1} / 3</span></div>
      {!backendOnline && <div className="offline-banner" role="alert">本机服务已停止。双击项目中的 <code>start_local.command</code> 并保持启动窗口开启。<button type="button" onClick={() => window.location.reload()}>重新连接</button></div>}
      {error && <div className="feedback error" role="alert">{error}</div>}{message && <div className="feedback success" role="status">{message}</div>}

      {step === 'profile' && <><div className="page-heading"><p className="section-kicker">从自己出发</p><h1>先说清楚你做过什么，<br />以及想做什么。</h1><p>简历里的经历与偏好会分开理解。可以修改描述，再重新生成草稿。</p></div><div className="workspace-grid">
        <form className="entry-panel" onSubmit={analyzeProfile}><div className="panel-title"><h2>提供你的材料</h2><span>仅供本次分析</span></div>
          <div className="form-grid"><Field label="学校"><input value={profileInput.school} onChange={e => editProfile('school', e.target.value)} placeholder="例如：中山大学" /></Field><Field label="专业"><input value={profileInput.major} onChange={e => editProfile('major', e.target.value)} placeholder="例如：金融学" /></Field><Field label="学历"><input value={profileInput.degree} onChange={e => editProfile('degree', e.target.value)} /></Field><Field label="预计毕业年份"><input type="number" min="2025" max="2045" value={profileInput.graduationYear} onChange={e => editProfile('graduationYear', e.target.value)} placeholder="例如：2029" /></Field></div>
          <Field label="当前城市"><input value={profileInput.city} onChange={e => editProfile('city', e.target.value)} placeholder="例如：广州" /></Field>
          <Field label="简历经历" hint="粘贴经历正文即可，联系方式会在发送前脱敏。"><textarea rows="9" required minLength="20" value={profileInput.resume} onChange={e => editProfile('resume', e.target.value)} placeholder="写下真实的项目、课程、技能和你具体做了什么。" /></Field>
          <Field label="兴趣与工作偏好" hint="写想做、不想做、实习时间和城市；未知的部分也可以说未知。"><textarea rows="6" required minLength="20" value={profileInput.preferences} onChange={e => editProfile('preferences', e.target.value)} placeholder="例如：喜欢产业研究与数据分析；学期中不到岗，只考虑寒暑假……" /></Field>
          <label className="consent"><input type="checkbox" checked={profileInput.consent} onChange={e => editProfile('consent', e.target.checked)} /><span>同意将脱敏后的简历文字和偏好发给模型分析</span></label>
          <button className="primary-button" disabled={!!busy || !profileInput.consent} type="submit">{busy === 'profile' ? '正在分析画像…' : '生成个人画像草稿'}</button>
        </form><section className="result-panel" aria-label="个人画像结果">{visibleProfile ? <><ProfileReview data={visibleProfile} />{profileDraft && <div className="result-actions"><label className="consent"><input type="checkbox" checked={profileChecked} onChange={e => setProfileChecked(e.target.checked)} /><span>我已核对经历和偏好，没有虚构内容</span></label><button className="secondary-button" disabled={!profileChecked || !!busy} onClick={saveProfile}>确认并保存画像</button></div>}{savedProfile && !profileDraft && <p className="saved-mark">画像已保存，可进入岗位分析。</p>}</> : <Empty symbol="◌" title="画像会出现在这里" text="先提供经历和偏好。生成后请核对 AI 对‘喜欢’与‘会做’的区分。" />}</section>
      </div></>}

      {step === 'job' && <><div className="page-heading"><p className="section-kicker">读懂招聘语言</p><h1>岗位名称之外，<br />它实际要求你做什么？</h1><p>粘贴一条完整 JD。系统会拆出核心任务、资格条件和仍需追问的地方。</p></div><div className="workspace-grid">
        <form className="entry-panel" onSubmit={analyzeJob}><div className="panel-title"><h2>粘贴岗位信息</h2><span>一次分析一条 JD</span></div>
          <Field label="招聘信息正文"><textarea rows="17" required minLength="30" value={jobInput.jd} onChange={e => editJob('jd', e.target.value)} placeholder="请粘贴岗位名称、职责、任职要求、地点和实习时间。只有链接时请先复制页面正文。" /></Field>
          <div className="form-grid"><Field label="信息来源"><select value={jobInput.sourceType} onChange={e => editJob('sourceType', e.target.value)}>{sourceOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field><Field label="原始链接或来源说明"><input value={jobInput.sourceReference} onChange={e => editJob('sourceReference', e.target.value)} placeholder="链接或截图说明" /></Field></div>
          <p className="input-note">来源由你填写，系统暂时不会打开链接验证招聘状态。</p><button className="primary-button" disabled={!!busy} type="submit">{busy === 'job' ? '正在解读岗位…' : '生成岗位画像草稿'}</button>
        </form><section className="result-panel" aria-label="岗位画像结果">{visibleJob ? <><JobReview data={visibleJob} />{jobDraft && <div className="result-actions"><p>确认任务与门槛准确后再保存；有误时修改左侧 JD 并重试。</p><button className="secondary-button" disabled={!!busy} onClick={saveJob}>确认并保存岗位</button></div>}{savedJob && !jobDraft && <p className="saved-mark">岗位已保存，可开始匹配。</p>}</> : <Empty symbol="⌕" title="岗位拆解会出现在这里" text="我们会把‘战略’‘AI’‘研究’等标题词翻译为具体任务，并保留未知条件。" />}</section>
      </div><section className="saved-jobs"><div className="saved-jobs-heading"><div><h2>已保存岗位</h2><span>共 {jobs.length} 条</span></div><p>选择一条岗位，继续与个人画像比较。</p></div><div className="job-toolbar"><input aria-label="搜索已保存岗位" value={jobSearch} onChange={e => setJobSearch(e.target.value)} placeholder="搜索公司、岗位、职能、地点…" /><span>按保存时间（新→旧）</span></div>{filteredJobs.length ? <div className="job-card-grid">{filteredJobs.map(job => <button type="button" className="job-card" key={job.job_id} onClick={() => selectSavedJob(job.job_id)}><span className="card-tag">已保存</span><h3>{job.company || '公司待确认'}</h3><p>{job.title}</p><span className="function-pill">{job.primary_function || '职能待确认'}</span><div className="card-footer"><span>⌖ {job.location || '地点待确认'}</span><strong>查看匹配</strong></div></button>)}</div> : <p className="saved-empty">{jobs.length ? '没有符合搜索条件的岗位。' : '还没有保存岗位。先在上方粘贴一条 JD，确认后会出现在这里。'}</p>}</section></>}

      {step === 'match' && <><div className="page-heading"><p className="section-kicker">把两边放在一起</p><h1>这份工作适合探索吗？<br />现在值得申请吗？</h1><p>两个问题分别判断。当前招聘时间不合适，不会抹掉一个方向的探索价值。</p></div><div className="workspace-grid">
        <section className="entry-panel match-input"><div className="panel-title"><h2>本次比较</h2><span>已确认的数据</span></div>
          <div className="selected-item"><span>个人画像</span><strong>{savedProfile?.background?.school || '画像'} · {savedProfile?.background?.college_or_major || '专业待确认'}</strong><small>{savedProfile?.profile_meta?.profile_version}</small></div>
          <div className="selected-item"><span>岗位画像</span><strong>{savedJob?.job_meta?.original_title}</strong><small>{savedJob?.job_meta?.company || '公司待确认'}</small></div>
          <label className="consent"><input type="checkbox" checked={matchConsent} onChange={e => setMatchConsent(e.target.checked)} /><span>同意将脱敏后的结构化画像和岗位信息发给模型分析</span></label>
          <button className="primary-button" disabled={!!busy || !matchConsent} onClick={analyzeMatch}>{busy === 'match' ? '正在分析匹配…' : '生成匹配分析草稿'}</button>
          <p className="input-note">手机号、邮箱和本地文件路径在发送前脱敏。分数由本地规则计算。</p>
          {savedMatch && <button className="text-button" onClick={saveApplication} disabled={!!busy}>把这条岗位加入求职记录</button>}
          <div className="application-section"><h3>求职记录</h3>{applications.length ? <div className="application-list">{applications.map(item => <div key={item.application_id} className="application-item"><div className="application-main"><div><strong>{item.role}</strong><small>{item.company}{item.applied_on ? ` · 投递于 ${item.applied_on}` : ''}{item.interviewed ? ' · 进入过面试' : ''}</small></div><select aria-label={`${item.role}的求职状态`} value={item.status} onChange={e => updateApplication(item.application_id, e.target.value)} disabled={!!busy}>{Object.entries(states).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div><textarea className="application-note" aria-label={`${item.role}的备注`} defaultValue={item.notes} placeholder="记录联系人、面试反馈或下一步" onBlur={e => updateApplicationNotes(item.application_id, e.target.value)} /></div>)}</div> : <p className="muted">还没有记录。保存匹配后可先收藏岗位。</p>}</div>
        </section><section className="result-panel" aria-label="匹配分析结果">{visibleMatch ? <><MatchReview alignment={visibleMatch.alignment} score={visibleMatch.score} resumeAdvice={!matchDraft && resumeAdvice?.matchId === savedMatch?.alignment?.match_meta?.match_id ? resumeAdvice.data : null} />{matchDraft && <div className="result-actions"><p>请核对支持点、缺口和简历重点。确认后保存这次分析。</p><button className="secondary-button" disabled={!!busy} onClick={saveMatch}>确认并保存匹配</button></div>}{savedMatch && !matchDraft && <p className="saved-mark">匹配结果已保存在本机。</p>}</> : <Empty symbol="◎" title="匹配解释会出现在这里" text="结果会说明哪些任务可能喜欢、哪些能力有证据、哪些条件仍需确认。" />}</section>
      </div></>}
      <footer className="page-footer">实习路径 · 第一版研究原型　|　AI 分析需要核对，投递始终由你决定。</footer>
    </main>
  </div>
}

export default App
