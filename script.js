const screens = {
  login: document.querySelector('#login-screen'),
  register: document.querySelector('#register-screen'),
};

const roleSelect = document.querySelector('#role-select');
const roleFields = document.querySelector('#role-fields');
const studentTemplate = document.querySelector('#student-fields-template');
const employerTemplate = document.querySelector('#employer-fields-template');
const searchParams = new URLSearchParams(window.location.search);

function showScreen(screenName) {
  Object.entries(screens).forEach(([name, element]) => {
    element.classList.toggle('is-active', name === screenName);
  });
}

function renderRoleFields(role) {
  const template = role === 'employer' ? employerTemplate : studentTemplate;
  roleFields.replaceChildren(template.content.cloneNode(true));
}

document.querySelectorAll('[data-go]').forEach((button) => {
  button.addEventListener('click', () => {
    showScreen(button.dataset.go);
  });
});

roleSelect.addEventListener('change', (event) => {
  renderRoleFields(event.target.value);
});

document.querySelectorAll('form').forEach((form) => {
  form.addEventListener('submit', (event) => {
    event.preventDefault();
  });
});

renderRoleFields(roleSelect.value);
showScreen(searchParams.get('screen') === 'register' ? 'register' : 'login');
