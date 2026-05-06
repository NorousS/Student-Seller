const modeTabs = document.querySelectorAll('.mode-tab');
const modeViews = document.querySelectorAll('.mode-view');
const searchInput = document.querySelector('#search-query');
const searchButton = document.querySelector('#search-button');

function showMode(mode) {
  modeTabs.forEach((tab) => {
    tab.classList.toggle('is-active', tab.dataset.mode === mode);
  });

  modeViews.forEach((view) => {
    view.classList.toggle('is-active', view.dataset.view === mode);
  });
}

function showResultsIfNeeded() {
  if (searchInput.value.trim()) {
    showMode('results');
    modeTabs.forEach((tab) => tab.classList.remove('is-active'));
  }
}

modeTabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    showMode(tab.dataset.mode);
  });
});

searchButton.addEventListener('click', showResultsIfNeeded);

searchInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    event.preventDefault();
    showResultsIfNeeded();
  }
});

showMode('universities');
