const contenu = "Nous ne pouvons pas accepter votre demande pour le moment."
function fetchEmails(status) {
    const emailContainer = document.getElementById("emails");

    if (!token) {
        alert("Votre session a expiré. Veuillez vous reconnecter.");
        window.location.href = "/";  // 🔄 Redirige vers la connexion
        return;
    }

    // ✅ Vérifier si `opportunityFilter` existe avant de l'utiliser
    const opportunityFilterElement = document.getElementById("opportunityFilter");
    const list = document.getElementById("list");
    const startDateElement  = document.getElementById('startDate');
    const endDateElement  = document.getElementById('endDate');
    const opportunityFilterId = opportunityFilterElement ? opportunityFilterElement.value : 0;  
    const startDate  = startDateElement ? startDateElement.value : null;
    const endDate  =  endDateElement ? endDateElement.value : null;
    const loading = document.getElementById("loading");

    let url = status ? `/get_emails_bdd` : `/get_emails?mail_type_id=${opportunityFilterId}`;

    if (status === false && startDate && startDate.trim() !== "") {
        url += `&date_since=${startDate}`;
    }
    if (status === false && endDate && endDate.trim() !== "") {
        url += `&date_before=${endDate}`;
    }
    if (loading) {
        loading.style.display = "block";
        emailContainer.style.display = "none";
        if (list) {list.style.display = "none";}
        
        document.getElementById("searchContainer").style.display = "none";  
        document.getElementById("saveEmails").style.display = "none"; 
        document.getElementById("emailStatesContainer").style.display = "none"; 
    }
    fetch(url, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token  // ✅ Envoi correct du token JWT
        }
    })
    .then(response => {
        if (response.status === 401) {  
            alert("Votre session a expiré. Veuillez vous reconnecter.");
            sessionStorage.removeItem("token");  
            window.location.href = "/"; 
        }
        return response.json();
    })
    .then(data => {
        if (status === true) {
            updateEmailUI(data.emails_bdd, [], data.state,status);
        } else {
            updateEmailUI(data.emails,data.types, [], status);
        }
    })
    .catch(error => {
        console.error("🔴 Erreur :", error);
        alert(`Erreur lors de la récupération des emails. ${error}`);
    })
    .finally(() => {
        if (loading) {
            loading.style.display = "none";

            if (status === true) {
                document.getElementById("emailStatesContainer").style.display = "flex"; 
                document.getElementById("emails").style.display = "block";
            } else {
                document.getElementById("searchContainer").style.display = "block";  
                document.getElementById("saveEmails").style.display = "block"; 
                document.getElementById("emails").style.display = "flex";
            }
        }
    });
}

// Fonction pour gérer le refus du client
function refuseClient(mailId) {
    fetch(`/api/refuse-client/${mailId}`, { // Remplace l'URL par ton endpoint backend
        method: "GET", 
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token 
        }
    })
    .then(response => {
        console.log(response)
        if (response.ok) {
            alert("Client refusé !");
            fetchEmails(true);
        } else {
            response.json().then(data => {
                alert("Erreur : " + data.message);
            });
        }
    })
    .catch(error => {
        console.error("Erreur :", error);
        alert("Erreur de connexion !");
    });
    document.getElementById("emailModal").style.display = "none"; // Fermer le modal après le refus
}

function sendMailClient(mailId, defaultMessage = "Nous ne pouvons pas accepter votre demande pour le moment.", defaultTo = "", defaultSubject = "") {
    console.log("Opening confirmation modal for mailId: " + mailId);

    const confirmationModal = `
        <div id="confirmationModal-${mailId}" class="modal">
            <div class="modal-content">
                <span class="close" id="closeModalBtn-${mailId}">&times;</span>
                <h3>Répondre au client</h3>
                <form id="mailForm-${mailId}">
                    <label for="to-${mailId}">À :</label>
                    <input type="email" id="to-${mailId}" value="${defaultTo}" placeholder="Destinataire" required>
                    
                    <label for="subject-${mailId}">Objet :</label>
                    <input type="text" id="subject-${mailId}" value="${defaultSubject}" placeholder="Objet du mail" required>
            
                    <textarea id="message-${mailId}" placeholder="Motif du refus">${defaultMessage}</textarea>
                    
                    <button type="button" class="btn btn-danger mt-2" id="confirmRefuseBtn-${mailId}">Envoyer</button>
                    <button type="button" class="btn btn-secondary mt-2" onclick="closeModal('confirmationModal-${mailId}')">Annuler</button>
                </form>
            </div>
        </div>
    `;

    // Ajouter le modal dans le DOM
    document.body.insertAdjacentHTML("beforeend", confirmationModal);
    document.getElementById(`confirmationModal-${mailId}`).style.display = "block";

    // Ajout des événements
    document.getElementById(`confirmRefuseBtn-${mailId}`).addEventListener("click", function () {
        confirmRefuse(mailId);
    });

    document.getElementById(`closeModalBtn-${mailId}`).addEventListener("click", function () {
        closeModal(`confirmationModal-${mailId}`);
    });
}


function confirmRefuse(mailId) {
    const to = document.getElementById(`to-${mailId}`).value;
    const subject = document.getElementById(`subject-${mailId}`).value;
    const message = document.getElementById(`message-${mailId}`).value;

    if (!to || !subject || !message) {
        alert("Veuillez remplir tous les champs !");
        return;
    }

    fetch(`/api/send-refuse-client/${mailId}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        },
        body: JSON.stringify({ to, subject, message })
    })
    .then(response => {
        if (response.ok) {
            alert("Email envoyé avec succès !");
            closeModal(`confirmationModal-${mailId}`);
        } else {
            response.json().then(data => {
                alert("Erreur : " + data.message);
            });
        }
    })
    .catch(error => {
        console.error("Erreur :", error);
        alert("Erreur de connexion !");
    });
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.remove();
    }
}

function openEmailModal(mail) {
    const modal = document.getElementById("emailModal");
    const modalBody = document.getElementById("modalBodyEmail");
    const modalFooter = document.getElementById("modalFooterEmail");

    modalBody.innerHTML = `
        <h2>${mail.email.subject}</h2>
        <p>📨 Expéditeur : ${mail.email.sender}</p>
        <p>📆 Reçu le : ${mail.email.receive_at}</p>
        <a href="${mail.email.path}" target="_blank">📩 Voir l'email</a>
        <p> Body : ${mail.email.body}</p>
        <p>% Probabilité : ${mail.email.percentage}</p>
        <p>📌 Type : ${mail.email.type_name}</p>
    `;// Vérification de l'état du client
    if (mail.state.name_state ===  "Nouveau Client") {
        modalFooter.innerHTML = `
            <button id="refuseButton" class="btn btn-danger" onclick="refuseClient(${mail.id})">Refuser</button>
        `;
    } else {
        modalFooter.innerHTML = ''; // Si ce n'est pas un "Nouveau client", on vide le footer
    }


    modal.style.display = "block";
}

// Fermer le modal avec le bouton (événement unique)
document.querySelector(".close").onclick = function () {
    document.getElementById("emailModal").style.display = "none";
};

// Fermer le modal en cliquant en dehors
window.onclick = function (event) {
    const modal = document.getElementById("emailModal");
    if (event.target === modal) {
        modal.style.display = "none";
    }
};


// ✅ Fonction pour afficher les emails dans le dashboard
function updateEmailUI(emails, types, state, status) {
    const emailsList = document.getElementById("emails");
    emailsList.innerHTML = "";

    if (emails.length > 0) {
        if (status === true) {
            createColumnsByState(state);
        }

        emails.forEach(mail => {
            const emailItem = document.createElement("div");
            emailItem.classList.add("email-item");

            if (status === false) {
                emailItem.innerHTML = `
                    <input type="checkbox" class="email-checkbox">
                    <p><b>${mail.subject}</b></p>
                    <p>📨 Expéditeur : ${mail.sender}</p>
                    <p>📆 Reçu le : ${mail.receive_at}</p>
                    <p> Boite: ${mail.body}</p>
                    <a href="${mail.path}" target="_blank">📩 Voir l'email</a>
                    <p>% Probabilité : ${mail.percentage }</p>
                    <p>📌 Type : ${mail.type_name }</p>
                `;
                emailsList.appendChild(emailItem);
            } else {
                emailItem.id = mail.email.id;
                emailItem.innerHTML = `
                    <p><b>${mail.email.subject}</b></p>
                    <p>📨 Expéditeur : ${mail.email.sender}</p>
                    <p>📆 Reçu le : ${mail.email.receive_at}</p>
                    <a href="${mail.email.path}" target="_blank">📩 Voir l'email</a>
                    <p>% Probabilité : ${mail.email.percentage }</p>
                    <p>📌 Type : ${mail.email.type_name }</p>
                    <button id="sendmailButton" class="btn btn-danger" 
                    onclick="event.stopPropagation(); sendMailClient(${mail.id}, '${contenu}', '${mail.email.sender}', '${mail.email.subject}');">
                    Envoyer un mail
                    </button>
                `;

                emailItem.onclick = function () {
                    openEmailModal(mail, types);
                };

                const column = document.getElementById(`state-${mail.state.id}`);
                if (column) {
                    column.appendChild(emailItem);
                }
                emailItem.setAttribute("draggable", "true");
                emailItem.setAttribute("ondragstart", `drag(event, ${mail.email.id})`);
            }
        });

        document.getElementById("opportunityFilter").addEventListener("change", filterEmails);
    } else {
        emailsList.innerHTML = "<p>Aucun email trouvé.</p>";
    }

    if (types) {
        const opportunityFilter = document.getElementById("opportunityFilter");
        opportunityFilter.innerHTML = opportunityFilter.options[0].outerHTML;

        types.forEach(mailType => {
            let option = document.createElement("option");
            option.value = mailType.id;
            option.textContent = mailType.type_name;
            opportunityFilter.appendChild(option);
        });

        opportunityFilter.removeEventListener("change", filterEmails);
        opportunityFilter.addEventListener("change", filterEmails);
    }
}

document.getElementById("messageIcon").addEventListener("click", function () {
    setTimeout(() => fetchEmails(false), 200); // Attendre 200ms
    sessionStorage.setItem("isFetchTrue", "false"); // Enregistrer l'état
});

document.getElementById("mailIcon").addEventListener("click", function () {
    document.getElementById("mailCount").textContent = "MD";
    setTimeout(() => fetchEmails(true), 200);
    sessionStorage.setItem("isFetchTrue", "true"); // Enregistrer l'état
});


function createColumnsByState(states) {
    const container = document.getElementById("emailStatesContainer");
    container.innerHTML = ""; 

    states.forEach(state => {
        const column = document.createElement("div");
        column.classList.add("column");
        column.id = `state-${state.id}`;
        column.innerHTML = `<h3>${state.name_state}</h3>`;
        
        // Ajouter des événements de glisser-déposer à chaque colonne
        column.setAttribute("ondrop", "drop(event)");
        column.setAttribute("ondragover", "allowDrop(event)");

        container.appendChild(column);
    });
}