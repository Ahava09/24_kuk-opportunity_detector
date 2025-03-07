
const token = sessionStorage.getItem("token");

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('myModal');
    const openModalBtn = document.getElementById('openModalBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');

    if (openModalBtn && modal && closeModalBtn) {
        openModalBtn.addEventListener('click', () => toggleModal(modal, true));
        closeModalBtn.addEventListener('click', () => toggleModal(modal, false));

        window.addEventListener('click', (event) => {
            if (event.target === modal) {
                toggleModal(modal, false);
            }
        });
    }

    function toggleModal(modal, show) {
        modal.classList.toggle('show', show);
        document.querySelector('.modal-content').classList.toggle('show', show);
        document.body.classList.toggle('modal-open', show);
    }

    window.populateEditForm = (clientId, clientName, clientEmail, clientPhone, isCompany) => {
        setValue(`edit_name_${clientId}`, clientName);
        setValue(`edit_email_${clientId}`, clientEmail);
        setValue(`edit_phone_${clientId}`, clientPhone);

        document.getElementById(`company_yes_${clientId}`).checked = (isCompany === "True");
        document.getElementById(`company_no_${clientId}`).checked = (isCompany === "False");
    };

    window.openEditModal = (clientId) => toggleClientModal(clientId, true);
    window.closeEditModal = (clientId) => toggleClientModal(clientId, false);

    function toggleClientModal(clientId, show) {
        const modal = document.getElementById(`editModal_${clientId}`);
        if (modal) {
            modal.classList.toggle('show', show);
            modal.style.display = show ? 'block' : 'none';
            modal.setAttribute('aria-hidden', show ? 'false' : 'true');
            document.body.classList.toggle('modal-open', show);
        }
    }

    function setValue(id, value) {
        const input = document.getElementById(id);
        if (input) input.value = value;
    }
});
