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
    console.log(url)
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
                <span class="close" id="DynamicBtn-${mailId}">&times;</span>
                <h3>Répondre au client</h3>
                <form id="mailForm-${mailId}">
                    <label for="to-${mailId}">À :</label>
                    <input type="email" id="to-${mailId}" value="${defaultTo}" placeholder="Destinataire" required>
                    
                    <label for="subject-${mailId}">Objet :</label>
                    <input type="text" id="subject-${mailId}" value="${defaultSubject}" placeholder="Objet du mail" required>
            
                    <textarea id="message-${mailId}" placeholder="Motif du refus">${defaultMessage}</textarea>
                    
                    <!-- 🔥 Le bouton AI qui sera ajouté dynamiquement -->
                    <div id="aiButtonContainer-${mailId}" style="display: none;">
                        <button type="button" class="btn btn-primary mt-2" id="generateAiBtn-${mailId}">🔮 Générer avec AI</button>
                    </div>

                    <button type="button" class="btn btn-danger mt-2" id="confirmRefuseBtn-${mailId}">Envoyer</button>
                    <button type="button" class="btn btn-secondary mt-2" onclick="closeModal('confirmationModal-${mailId}')">Annuler</button>
                </form>
            </div>
        </div>
    `;

    // Ajouter le modal dans le DOM
    document.body.insertAdjacentHTML("beforeend", confirmationModal);
    document.getElementById(`confirmationModal-${mailId}`).style.display = "block";

    // Ajouter l'événement pour envoyer l'email
    document.getElementById(`confirmRefuseBtn-${mailId}`).addEventListener("click", function () {
        confirmRefuse(mailId);
    });

    // Ajouter l'événement pour fermer le modal
    document.getElementById(`closeModalBtn-${mailId}`).addEventListener("click", function () {
        closeModal(`confirmationModal-${mailId}`);
    });

    // 🚀 Détecter si du texte est ajouté dans la `textarea`
    const messageTextarea = document.getElementById(`message-${mailId}`);
    const aiButtonContainer = document.getElementById(`aiButtonContainer-${mailId}`);

    messageTextarea.addEventListener("input", function () {
        if (messageTextarea.value.trim().length > 0) {
            aiButtonContainer.style.display = "block";  // 🔥 Afficher le bouton si du texte est présent
        } else {
            aiButtonContainer.style.display = "none";   // 🔥 Cacher le bouton si la zone est vide
        }
    });

    // 🚀 Ajouter l'événement pour générer un texte avec AI
    document.getElementById(`generateAiBtn-${mailId}`).addEventListener("click", function () {
        generateAiMessage(mailId);
    });
}

function getMailInfo(emailId) {
    console.log("Opening confirmation modal for mailId: " + emailId);

    // 📡 Envoyer une requête au backend
    fetch(`api/get_email_info/${emailId}`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + sessionStorage.getItem("token")
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log("✅ Données reçues :", data);

        // Vérifier si une modal existe déjà et la supprimer pour éviter les doublons
        let existingModal = document.getElementById("dynamicModal");
        if (existingModal) {
            existingModal.remove();
        }

        // 🔹 Création de la structure HTML de la modal
        let modal = document.createElement("div");
        modal.id = "dynamicModal";
        modal.classList.add("modal");

        modal.innerHTML = `
            <div class="modal-content">
                <span class="close" onclick="closeModal()">&times;</span>
                <h2>Détails de l'Email</h2>
                <p><strong>Expéditeur :</strong> ${data.client_name || "Inconnu"}</p>
                <p><strong>Email :</strong> ${data.email_address || "Non disponible"}</p>
                <p><strong>Téléphone :</strong> ${data.client_phone || "Non disponible"}</p>
                <p><strong>Entreprise :</strong> ${data.company_name || "Non spécifiée"}</p>
                <p><strong>Adresse :</strong> ${data.company_street || "Non disponible"}</p>
                <p><strong>Site Web :</strong> ${data.company_website || "Non disponible"}</p>
                <p><strong>Objet :</strong> ${data.email_subject || "Sans objet"}</p>
                <p><strong>Message :</strong></p>
                <textarea rows="5" readonly>${data.email_body || "Pas de contenu"}</textarea>
                
                <div style="margin-top: 10px;">
                    <button onclick="saveClientCompany(${emailId}, '${data.client_name}', '${data.email_address}', '${data.client_phone}', '${data.company_name}', '${data.company_street}', '${data.company_website}')">Enregistrer</button>
                    <button onclick="closedynamicModal()">Fermer</button>
                </div>
            </div>
        `;

        // Ajouter la modal au body
        document.body.appendChild(modal);

        // Afficher la modal
        modal.style.display = "block";
    })
    .catch(error => {
        console.log("🔴 Erreur API :", error);
        alert("⚠️ Impossible de charger les informations.");
    });
}

function saveClientCompany(emailId, clientName, clientEmail, clientPhone, companyName, companyStreet, companyWebsite) {
    console.log("📡 Envoi des données à l'API d'enregistrement...");

    let payload = {
        email_id: emailId,
        client_name: clientName !== "Inconnu" ? clientName : null,
        client_email: clientEmail !== "Non disponible" ? clientEmail : null,
        client_phone: clientPhone !== "Non disponible" ? clientPhone : null,
        company_name: companyName !== "Non spécifiée" ? companyName : null,
        company_street: companyStreet !== "Non disponible" ? companyStreet : null,
        company_website: companyWebsite !== "Non disponible" ? companyWebsite : null
    };

    fetch("api/save_client_company", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + sessionStorage.getItem("token")
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        console.log("✅ Enregistrement réussi :", data);
        alert("✅ Client et entreprise enregistrés avec succès !");
        
        // Fermer la modal après enregistrement
        Dynamic();
    })
    .catch(error => {
        console.log("🔴 Erreur lors de l'enregistrement :", error);
        alert("⚠️ Échec de l'enregistrement.");
    });
}

// Fonction pour fermer la modal
function closedynamicModal() {
    let modal = document.getElementById("dynamicModal");
    if (modal) {
        modal.remove();
    }
}


function generateAiMessage(mailId) {
    const subject = document.getElementById(`subject-${mailId}`).value;
    const to = document.getElementById(`to-${mailId}`).value;
    const existingText = document.getElementById(`message-${mailId}`).value.trim();

    // 🔥 Afficher un message de chargement
    const messageTextarea = document.getElementById(`message-${mailId}`);
    messageTextarea.value = "⏳ Génération du message en cours...";

    // 📡 Envoyer une requête au backend
    fetch("/generate_ai_message", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + sessionStorage.getItem("token")
        },
        body: JSON.stringify({ subject: subject, recipient: to, existingText: existingText })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            messageTextarea.value = data.message;
        } else {
            messageTextarea.value = "⚠️ Erreur lors de la génération du message.";
        }
    })
    .catch(error => {
        console.log("🔴 Erreur AI :", error);
        messageTextarea.value = "⚠️ Impossible de générer un message.";
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
            Dynamic(`confirmationModal-${mailId}`);
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

function Dynamic(modalId) {
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
        <p>📨 Expéditeur : ${mail.email.sender} ${mail.email.mail} </p>
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

    if (emails) {
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
                    <p>📨 Expéditeur : ${mail.sender} - ${mail.mail}</p>
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
                    <p>📨 Expéditeur : ${mail.email.sender} - ${mail.email.mail}</p>
                    <p>📆 Reçu le : ${mail.email.receive_at}</p>
                    <a href="${mail.email.path}" target="_blank">📩 Voir l'email</a>
                    <p>% Probabilité : ${mail.email.percentage }</p>
                    <p>📌 Type : ${mail.email.type_name }</p>
                    <button id="sendmailButton" class="btn btn-danger" 
                    onclick="event.stopPropagation(); sendMailClient(${mail.id}, '${contenu}', '${mail.email.mail}', '${mail.email.subject}');">
                    Envoyer un mail
                    </button>
                    <button id="getmailinfoButton" class="btn btn-danger" 
                    onclick="event.stopPropagation(); getMailInfo(${mail.email.id});">
                    Info
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