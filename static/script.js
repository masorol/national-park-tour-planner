let customCheckbox = document.querySelectorAll('.custom-checkbox');
let checkbox = document.querySelectorAll('.visually-hidden');

// Add click event listeners to all custom checkboxes
customCheckbox.forEach((customCheckbox, index) => {
  customCheckbox.addEventListener('click', function () {
    this.classList.toggle('checked');
    checkbox[index].checked = !checkbox[index].checked;
  });
});
