
document.addEventListener("DOMContentLoaded", function () {
    const socket = io("localhost:5001", {
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        timeout: 5000
    });

    let lastTotal = 0;
    let reconnectAttempts = 0;

    socket.on("connect", () => {
        console.log("Connecté au serveur");
        reconnectAttempts = 0;  // Réinitialiser les tentatives
    });
    socket.on("new_email", function (data) {
        console.log("📩 Total emails :", data.total);
        console.log("📩 Nouveaux emails :", data.new_count);
    
        // Mise à jour du compteur d'emails
        document.getElementById("mailCount").textContent = data.new_count;
    
        // Notification sonore et visuelle si de nouveaux emails arrivent
        if (data.new_count > 0) {
            const notification = document.createElement("div");
            notification.classList.add("email-notification");
            notification.innerHTML = `📩 ${data.new_count} nouveau(x) email(s) reçu(s)!`;
            document.body.appendChild(notification);
            notification.addEventListener("click", function () {
                alert("Vous avez de nouveaux emails !");
            });
    
            // Si de nouveaux emails sont reçus, on les ajoute à la liste existante
            if (data.new_emails && data.new_emails.length > 0) {
                const emailsList = document.getElementById("emails");
                console.log(data.new_emails)
                data.new_emails.forEach(mail => {
                    if (mail.email && mail.state) {  // Vérification de la structure
                        const emailItem = document.createElement("div");
                        emailItem.classList.add("email-item");
                        emailItem.id = mail.email.id; 
                        emailItem.innerHTML = `
                            <p><b>${mail.email.subject}</b></p>
                            <p>📨 Expéditeur : ${mail.email.sender}</p>
                            <p>📆 Reçu le : ${mail.email.receive_at}</p>
                            <p>Boite: ${mail.email.body}</p>
                            <a href="${mail.email.path}" target="_blank">📩 Voir l'email</a>
                            <p>% Probabilité : ${mail.email.percentage}</p>
                            <p>📌 Type : ${mail.state.type_name}</p>
                        `;
                        emailItem.style.backgroundColor = "#f0f8ff"; // Couleur bleu clair par exemple

                        const column = document.getElementById(`state-${mail.state.id}`);
                        if (column) {
                            column.appendChild(emailItem); // Ajouter l'email à la colonne correspondante
                        }
                        emailItem.setAttribute("draggable", "true"); // Rendre l'email déplaçable
                        emailItem.setAttribute("ondragstart", `drag(event, ${mail.email.id})`);
                    } else {
                        console.error("Email ou état manquant dans les données de l'email :", mail);
                    }
                });
            }
    
            // Retirer la notification après 3 secondes
            setTimeout(() => {
                notification.remove();
            }, 10000);
        }
    });
    
    

    socket.on("disconnect", () => {
        console.log("Déconnecté du serveur");
        if (reconnectAttempts < 5) {
            console.log("Tentative de reconnexion...");
            reconnectAttempts++;
        } else {
            console.log("Échec de la reconnexion après plusieurs tentatives.");
            alert("Échec de la connexion au serveur. Essayez à nouveau plus tard.");
        }
    });
    

    fetchEmails(false);
});


// ✅ Fonction pour récupérer les emails en direct depuis le serveur
function fetchEmails(status) {
    const token = sessionStorage.getItem("token");
    const emailContainer = document.getElementById("emails");

    if (!token) {
        alert("Votre session a expiré. Veuillez vous reconnecter.");
        window.location.href = "/";  // 🔄 Redirige vers la connexion
        return;
    }

    // ✅ Vérifier si `opportunityFilter` existe avant de l'utiliser
    const opportunityFilterElement = document.getElementById("opportunityFilter");
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


// ✅ Fonction pour afficher les emails dans le dashboard
function updateEmailUI(emails, types, state, status) {
    const emailsList = document.getElementById("emails");
    emailsList.innerHTML = "";
    // 📩 Afficher les emails non lus
    if (emails.length > 0) {
        if (status === true) {
            createColumnsByState(state);
        }        
        emails.forEach(mail => {
            const emailItem = document.createElement("div");
            emailItem.classList.add("email-item");
            if (status===false){
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
                    <p> Boite: ${mail.email.body}</p>
                    <a href="${mail.email.path}" target="_blank">📩 Voir l'email</a>
                    <p>% Probabilité : ${mail.email.percentage }</p>
                    <p>📌 Type : ${mail.state.type_name }</p>
                `;
    
                const column = document.getElementById(`state-${mail.state.id}`);
                if (column) {
                    column.appendChild(emailItem); // Ajouter l'email à la colonne correspondante
                }
                emailItem.setAttribute("draggable", "true"); // Rendre l'email déplaçable
    
                // Définir l'événement de début de glissement
                emailItem.setAttribute("ondragstart", `drag(event, ${mail.email.id})`);

            }
        });
        document.getElementById("opportunityFilter").addEventListener("change", filterEmails);
    } else {
        emailsList.innerHTML = "<p>Aucun email trouvé.</p>";
    }
    // ✅ Ajouter un événement pour filtrer les emails
    if (types) {
        const opportunityFilter = document.getElementById("opportunityFilter");

        // 🔥 Supprimer toutes les options existantes sauf la première option
        opportunityFilter.innerHTML = opportunityFilter.options[0].outerHTML;

        types.forEach(mailType => {
            let option = document.createElement("option");
            option.value = mailType.id;
            option.textContent = mailType.type_name;
            opportunityFilter.appendChild(option);
        });

        // 🎯 Supprimer les anciens événements pour éviter le doublement
        opportunityFilter.removeEventListener("change", filterEmails);
        opportunityFilter.addEventListener("change", filterEmails);
    }
    

    // 🔔 Mettre à jour les compteurs d'emails
    // document.getElementById("unreadCount").textContent = unread_count;
}

function filterEmails() {
    const selectedType = document.getElementById("opportunityFilter").value;
    fetchEmails(false);  // 🔥 Recharge les emails avec le filtre
}

document.getElementById('applyFilters').addEventListener('click', function () {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    if (startDate && endDate && new Date(startDate) > new Date(endDate)) {
        alert("La date de début ne peut pas être supérieure à la date de fin !");
        return;
    }

    fetchEmails(false);
});


document.getElementById("saveEmails").addEventListener("click", function () {
    const selectedEmails = [];

    // 📩 Récupérer les emails cochés et enregistrer leurs détails
    document.querySelectorAll(".email-checkbox:checked").forEach(checkbox => {
        const emailItem = checkbox.closest(".email-item");
        
        const rawDate = emailItem.querySelector("p:nth-child(4)").textContent.trim();
        const cleanDate = rawDate.replace("📆 Reçu le :", "").trim();  

        const emailData = {
            subject: emailItem.querySelector("p:nth-child(2)") ? emailItem.querySelector("p:nth-child(2)").textContent.trim() : '',
            sender: emailItem.querySelector("p:nth-child(3)") ? emailItem.querySelector("p:nth-child(3)").textContent.replace("📨 Expéditeur :", "").trim() : '',
            receive_at: cleanDate || '',
            body: emailItem.querySelector("p:nth-child(5)") ? emailItem.querySelector("p:nth-child(5)").textContent.replace("Boite  :", "").trim() : '',
            path: emailItem.querySelector("a") ? emailItem.querySelector("a").getAttribute("href") : '',
            percentage: emailItem.querySelector("p:nth-child(7)") ? emailItem.querySelector("p:nth-child(7)").textContent.replace("% Probabilité :", "").trim() : '',
            type: emailItem.querySelector("p:nth-child(8)") ? emailItem.querySelector("p:nth-child(8)").textContent.replace("📌 Type :", "").trim() : ''
        };
        console.log(emailData);
        selectedEmails.push(emailData);
    });
    console.log("🟢 Emails sélectionnés :", selectedEmails);
    if (selectedEmails.length === 0) {
        alert("Veuillez sélectionner au moins un email !");
        return;
    }

    // 📡 Envoyer les emails sélectionnés au serveur
    fetch("/save_emails", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + sessionStorage.getItem("token")  
        },
        body: JSON.stringify({ emails: selectedEmails })
    })
    .then(response => response.json())
    .then(data => {
        // alert(data.message);
        // Supprimer les emails enregistrés
        selectedEmails.forEach(email => {
            // Trouver et supprimer les éléments correspondants à ces emails
            const emailElements = document.querySelectorAll(".email-item");
            emailElements.forEach(emailItem => {
                const emailSender = emailItem.querySelector("p:nth-child(3)").textContent.replace("📨 Expéditeur :", "").trim();
                const emailSubject = emailItem.querySelector("p:nth-child(2)").textContent.trim();

                if (emailSender === email.sender && emailSubject === email.subject) {
                    emailItem.remove(); // Supprimer l'élément du DOM
                }
            });
        });
        // location.reload();
    })
    .catch(error => {
        console.error("🔴 Erreur :", error);
        alert("Erreur lors de l'ajout des emails.");
    });
});

// document.getElementById("searchForm").addEventListener("submit", function (event) {
//     event.preventDefault(); 

//     const searchCriteria = document.getElementById("searchCriteria").value.trim();
//     const emailContainer = document.getElementById("emails");

//     if (searchCriteria === "") {
//         alert("Veuillez entrer un critère de recherche.");
//         return;
//     }

//     fetch(`api/searchCriteria?criterion=${encodeURIComponent(searchCriteria)}`, {
//         method: "GET",
//         headers: { "Content-Type": "application/json" }
//     })
//     .then(response => response.json())
//     .then(data => {
//         if (data.error) {
//             emailContainer.innerHTML = `<p style="color:red;">❌ ${data.error}</p>`;
//             return;
//         }

//         if (data.count === 0) {
//             emailContainer.innerHTML = "<p>Aucun email trouvé.</p>";
//             return;
//         }

//         let emailList = `<h3>📩 Résultats (${data.count}) - ${data.message}</h3>`;
//         // data.emails.forEach(mail => {
//         //     emailList += `
//         //         <div class="email-item">
//         //             <p><b>${mail.subject}</b> de ${mail.from}</p>
//         //             <p>📆 Reçu le : ${mail.receive_at}</p>
//         //             <p>📌 Negoce : ${mail.is_negoce ? "✅ Oui" : "❌ Non"}</p>
//         //         </div>
//         //     `;
//         // });

//         emailContainer.innerHTML = emailList;
//     })
//     .catch(error => {
//         console.error("Erreur :", error);
//         emailContainer.innerHTML = `<p style="color:red;">❌ Erreur de récupération des emails.</p>`;
//     });
// });

document.getElementById("messageIcon").addEventListener("click", function () {
    setTimeout(() => fetchEmails(false), 200); // ✅ Attendre 200ms pour s'assurer que l'élément est visible
});

document.getElementById("mailIcon").addEventListener("click", function () {
    document.getElementById("mailCount").textContent = "MD";
    setTimeout(() => fetchEmails(true), 200);
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

function allowDrop(event) {
    event.preventDefault(); // Nécessaire pour permettre le dépose
}

function drag(event, emailId) {
    event.dataTransfer.setData("emailId", emailId); // Enregistrer l'ID de l'email dans les données de transfert
}

function drop(event) {
    event.preventDefault();
    const emailId = event.dataTransfer.getData("emailId"); // Récupérer l'ID de l'email
    const emailElement = document.getElementById(emailId); // Trouver l'élément email correspondant

    const targetColumn = event.target.closest('.column'); // Trouver la colonne cible

    if (targetColumn) {
        const stateId = targetColumn.id.split('-')[1]; // Extraire l'ID de l'état depuis l'ID de la colonne

        // Mettre à jour l'état de l'email dans la base de données (par exemple, via un appel API)
        updateEmailState(emailId, stateId);

        // Déplacer l'email dans la nouvelle colonne
        targetColumn.appendChild(emailElement);
    }
}

// Fonction pour mettre à jour l'état de l'email dans la base de données
function updateEmailState(emailId, newStateId) {
    const token = sessionStorage.getItem("token");
    if (!token) {
        alert("Votre session a expiré. Veuillez vous reconnecter.");
        window.location.href = "/";
        return;
    }

    fetch(`/update_email_state`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        },
        body: JSON.stringify({
            emailId: emailId,
            newStateId: newStateId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log(`Email ${emailId} déplacé vers l'état ${newStateId}`);
        } else {
            alert("Erreur lors de la mise à jour de l'état de l'email.");
        }
    })
    .catch(error => {
        console.error("Erreur:", error);
        alert("Erreur lors de la mise à jour de l'état de l'email.");
    });
}

document.addEventListener("change", function () {
    const selected = document.querySelectorAll(".email-checkbox:checked").length;
    document.getElementById("saveEmails").textContent = `📥 Ajouter (${selected}) à la base de données`;
});

