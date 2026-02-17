const LOGIN_ENDPOINT = '/auth/login';
const BOOTSTRAP_ENDPOINT = '/widget/room2/bootstrap';
const SUBMIT_ENDPOINT = '/widget/room2/submit';

const ALLOWED_SUPPORT_FLAGS = ['none', 'anesthesist', 'anesthesist_icu'];

const elements = {
  loginEmail: document.getElementById('login-email'),
  loginPassword: document.getElementById('login-password'),
  loginButton: document.getElementById('login-button'),
  caseId: document.getElementById('case-id'),
  loadCaseButton: document.getElementById('load-case-button'),
  caseContext: document.getElementById('case-context'),
  doctorUserId: document.getElementById('doctor-user-id'),
  decision: document.getElementById('decision'),
  supportFlag: document.getElementById('support-flag'),
  reason: document.getElementById('reason'),
  submitButton: document.getElementById('submit-button'),
  retryButton: document.getElementById('retry-button'),
  statusMessage: document.getElementById('status-message'),
};

let authToken = null;
let lastRetryAction = null;

function setStatus(message, tone = 'info', showRetry = false) {
  elements.statusMessage.textContent = message;
  elements.statusMessage.dataset.tone = tone;
  elements.retryButton.hidden = !showRetry;
}

function mapApiError(statusCode) {
  switch (statusCode) {
    case 401:
      return 'Autenticacao invalida ou expirada.';
    case 403:
      return 'Acesso negado: perfil sem permissao de medico.';
    case 404:
      return 'Caso nao encontrado para este widget.';
    case 409:
      return 'Caso nao esta mais aguardando decisao (possivel corrida/duplicidade).';
    default:
      return 'Falha de comunicacao com a API. Tente novamente.';
  }
}

function getRequiredValue(input, fieldLabel) {
  const value = input.value.trim();
  if (!value) {
    throw new Error(`Campo obrigatorio: ${fieldLabel}`);
  }
  return value;
}

function toNullableText(value) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function parseCaseIdFromQuery() {
  const params = new URLSearchParams(window.location.search);
  const caseId = params.get('case_id');
  if (caseId) {
    elements.caseId.value = caseId;
  }
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const contentType = response.headers.get('content-type') || '';
  const body = contentType.includes('application/json') ? await response.json() : null;
  return { response, body };
}

async function login() {
  try {
    const email = getRequiredValue(elements.loginEmail, 'Email');
    const password = getRequiredValue(elements.loginPassword, 'Senha');

    const payload = { email, password };
    const { response, body } = await requestJson(LOGIN_ENDPOINT, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      setStatus(mapApiError(response.status), 'error', true);
      lastRetryAction = login;
      return;
    }

    authToken = body.token;
    if (body.role !== 'admin') {
      setStatus('Acesso negado: perfil sem permissao de medico.', 'error', false);
      return;
    }

    setStatus('Autenticacao concluida com sucesso.', 'success', false);
    lastRetryAction = null;
  } catch (error) {
    setStatus(error.message, 'error', true);
    lastRetryAction = login;
  }
}

async function loadCaseContext() {
  try {
    if (!authToken) {
      throw new Error('Realize o login antes de carregar o caso.');
    }

    const caseId = getRequiredValue(elements.caseId, 'Case ID');
    const payload = { case_id: caseId };

    const { response, body } = await requestJson(BOOTSTRAP_ENDPOINT, {
      method: 'POST',
      headers: {
        authorization: `Bearer ${authToken}`,
        'content-type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      setStatus(mapApiError(response.status), 'error', true);
      lastRetryAction = loadCaseContext;
      return;
    }

    elements.caseContext.textContent = JSON.stringify(body, null, 2);
    setStatus('Contexto do caso carregado.', 'success', false);
    lastRetryAction = null;
  } catch (error) {
    setStatus(error.message, 'error', true);
    lastRetryAction = loadCaseContext;
  }
}

function buildSubmitPayload() {
  const case_id = getRequiredValue(elements.caseId, 'Case ID');
  const doctor_user_id = getRequiredValue(elements.doctorUserId, 'Doctor user id');
  const decision = getRequiredValue(elements.decision, 'Decisao');
  const support_flag = getRequiredValue(elements.supportFlag, 'Support flag');
  const reason = toNullableText(elements.reason.value);

  if (!ALLOWED_SUPPORT_FLAGS.includes(support_flag)) {
    throw new Error('Support flag invalido para o contrato da API.');
  }

  if (decision === 'deny' && support_flag !== 'none') {
    throw new Error('Para decision=deny, use support_flag=none.');
  }

  return {
    case_id: case_id,
    doctor_user_id: doctor_user_id,
    decision: decision,
    support_flag: support_flag,
    reason: reason,
  };
}

async function submitDecision() {
  try {
    if (!authToken) {
      throw new Error('Realize o login antes de enviar a decisao.');
    }

    const payload = buildSubmitPayload();
    const { response, body } = await requestJson(SUBMIT_ENDPOINT, {
      method: 'POST',
      headers: {
        authorization: `Bearer ${authToken}`,
        'content-type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      setStatus(mapApiError(response.status), 'error', true);
      lastRetryAction = submitDecision;
      return;
    }

    if (!body || body.ok !== true) {
      setStatus('Resposta inesperada ao enviar a decisao.', 'error', true);
      lastRetryAction = submitDecision;
      return;
    }

    setStatus('Decisao enviada com sucesso.', 'success', false);
    lastRetryAction = null;
  } catch (error) {
    setStatus(error.message, 'error', true);
    lastRetryAction = submitDecision;
  }
}

async function retryLastAction() {
  if (lastRetryAction) {
    await lastRetryAction();
  }
}

function bindEvents() {
  elements.loginButton.addEventListener('click', login);
  elements.loadCaseButton.addEventListener('click', loadCaseContext);
  elements.submitButton.addEventListener('click', submitDecision);
  elements.retryButton.addEventListener('click', retryLastAction);
}

parseCaseIdFromQuery();
bindEvents();
