document.addEventListener('DOMContentLoaded', function() {
    // Trova tutti i campi di tipo date
    const dateFields = document.querySelectorAll('input[type="date"]');
    
    dateFields.forEach(function(field) {
        // Aggiungi validazione quando l'input perde il focus
        field.addEventListener('blur', function() {
            const value = field.value;
            if (value) {
                // Verifica che il formato sia valido (YYYY-MM-DD)
                const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
                if (!dateRegex.test(value)) {
                    alert('Formato data non valido. Utilizzare il formato YYYY-MM-DD (es: 2023-05-20)');
                    field.value = ''; // Resetta il campo
                    field.focus();
                } else {
                    // Verifica che la data sia valida
                    const date = new Date(value);
                    if (isNaN(date.getTime())) {
                        alert('Data non valida. Inserire una data reale.');
                        field.value = '';
                        field.focus();
                    }
                }
            }
        });
    });
});