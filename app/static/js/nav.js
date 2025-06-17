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
                <span class="close" onclick="closeModal('confirmationModal-${mailId}')">&times;</span>
                <h3>Répondre au client</h3>
                <form id="mailForm-${mailId}">
                    <label for="to-${mailId}">À :</label>
                    <input type="email" id="to-${mailId}" value="${defaultTo}" placeholder="Destinataire" required>
                    
                    <label for="subject-${mailId}">Objet :</label>
                    <input type="text" id="subject-${mailId}" value="${defaultSubject}" placeholder="Objet du mail" required>
            
                    <label for="message-${mailId}">Message :</label>
                    <textarea id="message-${mailId}" placeholder="Motif du refus">${defaultMessage}</textarea>

                    <!-- 🔥 Conteneur du bouton AI -->
                    <div id="aiButtonContainer-${mailId}" style="display: none; margin-top: 10px;">
                        <button type="button" class="btn btn-primary" id="generateAiBtn-${mailId}">🔮 Générer avec AI</button>
                    </div>

                    <div style="margin-top: 10px;">
                        <button type="button" class="btn btn-danger" id="confirmRefuseBtn-${mailId}">Envoyer</button>
                        <button type="button" class="btn btn-secondary" onclick="closeModal('confirmationModal-${mailId}')">Annuler</button>
                    </div>
                </form>
            </div>
        </div>
    `;

    // Ajouter le modal dans le DOM
    document.body.insertAdjacentHTML("beforeend", confirmationModal);
    document.getElementById(`confirmationModal-${mailId}`).style.display = "block";

    // Sélection des éléments après l'ajout au DOM
    const messageTextarea = document.getElementById(`message-${mailId}`);
    const aiButtonContainer = document.getElementById(`aiButtonContainer-${mailId}`);
    const aiButton = document.getElementById(`generateAiBtn-${mailId}`);

    // 🚀 Détecter si du texte est ajouté dans la `textarea`
    function toggleAiButton() {
        if (messageTextarea.value.trim().length > 0) {
            aiButtonContainer.style.display = "block";
        } else {
            aiButtonContainer.style.display = "none"; 
        }
    }

    messageTextarea.addEventListener("input", toggleAiButton);
    toggleAiButton(); 
    aiButton.addEventListener("click", function () {
        generateAiMessage(mailId);
    });

    document.getElementById(`confirmRefuseBtn-${mailId}`).addEventListener("click", function () {
        confirmRefuse(mailId);
    });
}

function getMailInfo(emailId) {
    console.log("Opening confirmation modal for mailId: " + emailId);

    const loading = document.getElementById("loading");
    if (loading) {
        loading.style.display = "block";
    }

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
        // console.log("✅ Données reçues :", data);

        // Vérifier si une modal existe déjà et la supprimer pour éviter les doublons
        let existingModal = document.getElementById("dynamicModal");
        if (existingModal) {
            existingModal.remove();
        }

        // 🔹 Création de la structure HTML de la modal
        let modal = document.createElement("div");
        modal.id = "dynamicModal";
        modal.classList.add("modal");
        let detTableHTML = `<h3>📦 Produits / Matériaux demandés</h3>`;

        if (Array.isArray(data.DET?.produits)) {
            detTableHTML += `
                <table class="styled-table">
                    <thead>
                        <tr>
                            <th>Désignation</th>
                            <th>Spécifications</th>
                            <th>Quantité</th>
                            <th>Contraintes</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
        
            data.DET.produits.forEach(product => {
                detTableHTML += `
                    <tr>
                        <td>${product.designation_client || "Non spécifié"}</td>
                        <td>${product.specifications_techniques || "Non spécifié"}</td>
                        <td>${product.quantite_estimee || "Non spécifié"}</td>
                        <td>${product.contraintes_techniques || "Non spécifié"}</td>
                    </tr>
                `;
            });
        
            detTableHTML += `</tbody></table>`;
        } else {
            detTableHTML += `<p class="no-products">Aucun produit/matériau spécifié.</p>`;
        }
        
        // 📌 Contenu de la modal
        modal.innerHTML = `
            <div class="modal-content">

                <div style="margin-top: 10px;">
                    <button onclick="saveClientCompany(${emailId})">Enregistrer</button>
                    <button onclick="closedynamicModal()">Fermer</button>
                </div>
                <h2>Détails de l'Email</h2>
                
                <div class="tabs">
                    <button class="tab-button active" onclick="openTab(event, 'tab-email')">📩 Email</button>
                    <button class="tab-button" onclick="openTab(event, 'tab-dae')">📄 DEA</button>
                    <button class="tab-button" onclick="openTab(event, 'tab-det')">⚙️ DET</button>
                </div>

                <div id="tab-email" class="tab-content active">
                    <p><strong>Expéditeur :</strong> ${data.email_sender || "Inconnu"}</p>
                    <p><strong>Email :</strong> ${data.email_address || "Non disponible"}</p>
                    <p><strong>Téléphone :</strong> ${data.client_phone || "Non disponible"}</p>
                    <p><strong>Entreprise :</strong> ${data.company_name || "Non spécifiée"}</p>
                    <p><strong>Adresse :</strong> ${data.company_street || "Non disponible"}</p>
                    <p><strong>Site Web :</strong> ${data.company_website || "Non disponible"}</p>
                    <p><strong>Objet :</strong> ${data.email_subject || "Sans objet"}</p>
                    <p><strong>Message :</strong></p>
                    <textarea rows="5" readonly>${data.email_body || "Pas de contenu"}</textarea>
                </div>

                <div id="tab-dae" class="tab-content">
                    <h3>Détails Initiaux de la Demande (DEA)</h3>
                    <p><strong>Logo :</strong></p>
                    <div class="logo-container">
                        ${data.company_logo ? `<img src="${data.DEA?.logo_entreprise_base64}" alt="Logo de ${data.DEA?.entreprise_demandeuse || 'Entreprise'}" class="company-logo">` 
                        : "<p>Aucun logo disponible</p>"}
                    </div>
                    <p><strong>Objet de la demande :</strong> ${data.DEA?.objet_demande || "Non spécifié"}</p>
                    <p><strong>Demandeur :</strong> ${data.DEA?.demandeur?.nom || "Non spécifié"} ${data.DEA?.demandeur?.prenom || ""}</p>
                    <p><strong>Email :</strong> ${data.client_email || "Non spécifié"}</p>
                    <p><strong>Téléphone :</strong> ${data.DEA?.demandeur?.telephone || "Non spécifié"}</p>
                    <p><strong>Entreprise :</strong> ${data.DEA?.entreprise_demandeuse || "Non spécifié"}</p>
                    <p><strong>REF demande :</strong> ${data.DEA?.reference_demande || "Non spécifié"}</p>
                    <p><strong>Maree Associe :</strong> ${data.DEA?.maree_associee || "Non spécifié"}</p>
                    <p><strong>Date limite de livraison :</strong> ${data.DEA?.date_limite_livraison || "Non spécifiée"}</p>
                    <p><strong>Date limite de réponse :</strong> ${data.DEA?.date_limite_reponse || "Non spécifiée"}</p>
                    <p><strong>Contexte :</strong> ${data.DEA?.contexte || "Non spécifié"}</p>
                    <p><strong>Critères de sélection :</strong> ${data.DEA?.criteres_selection || "Non spécifié"}</p>
                    <p><strong>Budget estimé :</strong> ${data.DEA?.budget_estime || "Non spécifié"}</p>
                    <p><strong>Délai d'exécution :</strong> ${data.DEA?.delai_execution || "Non spécifié"}</p>
                    <p><strong>Modalités de paiement :</strong> ${data.DEA?.modalites_paiement || "Non spécifié"}</p>
                </div>

                <div id="tab-det" class="tab-content">
                    <h3>Détails Éléments et Techniques (DET)</h3>
                    <p><strong>Description du projet :</strong> ${data.DET?.description_projet || "Non spécifié"}</p>
                    <p><strong>TVA :</strong> ${data.DEA?.exoneration_tva || "Non spécifié"}</p>
                    <h3>📍 Lieu d'exécution : ${data.DET?.lieu_execution || "Non spécifié"}</h3>
                    <h3>📍 Lieu de livraison: ${data.DEA?.adresse_livraison || "Non spécifié"}</h3>
                    ${detTableHTML}
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
        alert(error);
    })
    .finally(() => {
        if (loading) {
            loading.style.display = "none";
        }
    });
}


function openTab(evt, tabId) {
    let tabContents = document.querySelectorAll(".tab-content");
    let tabButtons = document.querySelectorAll(".tab-button");

    tabContents.forEach(tab => {
        tab.style.display = "none";
    });

    tabButtons.forEach(btn => {
        btn.classList.remove("active");
    });

    document.getElementById(tabId).style.display = "block";
    evt.currentTarget.classList.add("active");
}

function saveClientCompany(emailId) {
    console.log("📡 Envoi des données à l'API d'enregistrement... ", {emailId});

    fetch(`api/save_client_company/${emailId}`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + sessionStorage.getItem("token")
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log("✅ Enregistrement réussi :", data);
        alert("✅ Client et entreprise enregistrés avec succès !");
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


function closeModal(modal) {
    let element = document.getElementById(modal);
    if (element) {
        element.remove();
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

    // 📎 Vérification des pièces jointes
    let attachmentsHTML = "";
    if (mail.attachments && mail.attachments.length > 0) {
        attachmentsHTML += `<p>📎 Pièces jointes :</p><ul>`;
        mail.attachments.forEach(att => {
            attachmentsHTML += `
                <li>
                    <a href="${window.location.origin}/api/download_attachment/${encodeURIComponent(att.filename)}?email=${encodeURIComponent(mail.email.id)}" 
                        target="_blank">
                        📂 ${att.filename}
                    </a>
                </li>`;
        });
        attachmentsHTML += `</ul>`;
    }

    modalBody.innerHTML = `
        <h2>${mail.email.subject}</h2>
        <p>📨 Expéditeur : ${mail.email.sender} ${mail.email.mail} </p>
        <p>📆 Reçu le : ${mail.email.receive_at}</p>
        <a href="${mail.email.path}" target="_blank">📩 Voir l'email</a>
        <p> Body : ${mail.email.body}</p>
        <p>% Probabilité : ${mail.email.percentage}</p>
        <p>📌 Type : ${mail.email.type_name}</p>
        ${attachmentsHTML}  <!-- 📎 Ajout des pièces jointes -->
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
                

                // 📎 Vérification des pièces jointes
                let attachmentsHTML = "";
                if (mail.attachments && mail.attachments.length > 0) {
                    attachmentsHTML += `<p>📎 Pièces jointes :</p><ul>`;
                    mail.attachments.forEach(att => {
                        attachmentsHTML += `
                            <li>
                                <a href="${window.location.origin}/download_attachment/${encodeURIComponent(att.filename)}?email=${encodeURIComponent(mail.mail)}" 
                                   target="_blank">
                                    📂 ${att.filename}
                                </a>
                            </li>`;
                    });
                    attachmentsHTML += `</ul>`;
                }
                emailItem.innerHTML = `
                    <input type="checkbox" class="email-checkbox">
                    <p><b>${mail.subject}</b></p>
                    <p>📨 Expéditeur : ${mail.sender} - ${mail.mail}</p>
                    <p>📆 Reçu le : ${mail.receive_at}</p>
                    <p> Boite: ${mail.body}</p>
                    <a href="${mail.path}" target="_blank">📩 Voir l'email</a>
                    <p>% Probabilité : ${mail.percentage }</p>
                    <p>📌 Type : ${mail.type_name }</p>
                    <a href="${mail.path}" target="_blank">📩 Voir l'email</a>
                    ${attachmentsHTML}  <!-- Ajout des pièces jointes -->
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