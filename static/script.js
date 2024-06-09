const customCheckbox = document.querySelectorAll('.custom-checkbox');
const checkbox = document.querySelectorAll('visually-hidden');

customCheckbox.addEventListener('click', function() {
  this.classList.toggle('checked');
  checkbox.checked = !checkbox.checked;
});