function limparFormulario(btn) {
    if (!confirm('Deseja realmente limpar todos os campos?')) return;

    const form = btn.closest('.modal').querySelector('form');

    form.querySelectorAll('input, textarea, select').forEach(field => {
        if (field.name === 'csrfmiddlewaretoken') return;

        if (field.type === 'checkbox' || field.type === 'radio') {
            field.checked = false;
        } else if (field.tagName === 'SELECT') {
            field.selectedIndex = 0;
        } else {
            field.value = '';
        }
    });
}
