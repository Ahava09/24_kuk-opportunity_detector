
let reconnectAttempts = 0;
const token = sessionStorage.getItem("token");
document.addEventListener("DOMContentLoaded", function () {


    const isFetchTrue = sessionStorage.getItem("isFetchTrue");

    // Si l'état est "true", appelez fetchEmails(true)
    if (isFetchTrue === "true") {
        fetchEmails(true);
    } else {
        fetchEmails(false);
    }

    const socket = io("http://localhost:5001", {
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        timeout: 5000
    });

    socket.on("new_email_gmail", (data) => {
        console.log("📩 Nouvel email reçu :", data.emails);
        alert("📩 Nouvel email détecté !");
    });

    socket.onAny((event, data) => {
        console.log(`📡 Événement reçu : ${event}`, data);
    });
    

    socket.on("new_email", function (data) {
        console.log("📩 Total emails :", data.total);
        console.log("📩 Nouveaux emails :", data.new_count);
    
        // Mise à jour du compteur d'emails
        const iconEmail = document.getElementById("mailCount");
        let currentCount = parseInt(iconEmail.textContent);
        if (isNaN(currentCount)) {
            currentCount = 0; // Si ce n'est pas un chiffre, initialiser à 0
        }
    
        // Addition de la nouvelle valeur
        const updatedCount = currentCount + data.new_count;
        iconEmail.textContent = updatedCount;
    
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
                    if (mail.email && mail.state) { 
                        const emailItem = document.createElement("div");
                        emailItem.classList.add("email-item");
                        emailItem.id = mail.email.id; 
                        emailItem.innerHTML = `
                            <p><b>${mail.email.subject}</b></p>
                            <p>📨 Expéditeur : ${mail.email.sender} - ${mail.email.mail}</p>
                            <p>📆 Reçu le : ${mail.email.receive_at}</p>
                            <p>Boite: ${mail.email.body}</p>
                            <a href="${mail.email.path}" target="_blank">📩 Voir l'email</a>
                            <p>% Probabilité : ${mail.email.percentage}</p>
                            <p>📌 Type : ${mail.state.type_name}</p>
                        `;
                        emailItem.style.backgroundColor = "#f0f8ff"; 

                        const column = document.getElementById(`state-${mail.state.id}`);
                        if (column) {
                            column.appendChild(emailItem); 
                        }
                        emailItem.setAttribute("draggable", "true"); 
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

    socket.on("error", (data) => {
        console.error("🚨 Erreur WebSocket :", data);
    });
    
    

    socket.on("disconnect", () => {
        console.log("Déconnecté du serveur");
    });
    

    // fetchEmails(false);
});

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

        // 📩 Récupérer et nettoyer l'expéditeur
        const rawSender = emailItem.querySelector("p:nth-child(3)") ? emailItem.querySelector("p:nth-child(3)").textContent.replace("📨 Expéditeur :", "").trim() : '';
    
        const senderMatch = rawSender.match(/^(.*?) - ([\w\.-]+@[\w\.-]+\.\w+)$/);
        let senderName = senderMatch ? senderMatch[1].trim() : rawSender;
        let senderEmail = senderMatch ? senderMatch[2].trim() : '';

        // 📆 Nettoyage de la date
        const rawDate = emailItem.querySelector("p:nth-child(4)").textContent.trim();
        const cleanDate = rawDate.replace("📆 Reçu le :", "").trim();  
 

        let attachments = [];
        let attachmentLinks = emailItem.querySelectorAll("ul li a");
        attachmentLinks.forEach(link => {
            attachments.push({
                filename: decodeURIComponent(link.getAttribute("href").split("?")[0].split("/").pop())  // ✅ Supprime les paramètres après "?"
            });
        });
        const emailData = {
            subject: emailItem.querySelector("p:nth-child(2)") ? emailItem.querySelector("p:nth-child(2)").textContent.trim() : '',
            sender: senderName,  // 🟢 Nom de l'expéditeur
            mail: senderEmail,   // 🟢 Email de l'expéditeur
            receive_at: cleanDate || '',
            body: emailItem.querySelector("p:nth-child(5)") ? emailItem.querySelector("p:nth-child(5)").textContent.replace("Boite  :", "").trim() : '',
            path: emailItem.querySelector("a") ? emailItem.querySelector("a").getAttribute("href") : '',
            percentage: emailItem.querySelector("p:nth-child(7)") ? emailItem.querySelector("p:nth-child(7)").textContent.replace("% Probabilité :", "").trim() : '',
            type: emailItem.querySelector("p:nth-child(8)") 
            ? emailItem.querySelector("p:nth-child(8)").textContent.replace("📌 Type :", "").trim() 
            : "None",
            attachments: attachments
        };
        console.log("------------------------------------");
        console.log(attachments);
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
        alert(data.message);
        // Supprimer les emails enregistrés
        selectedEmails.forEach(email => {
            // Trouver et supprimer les éléments correspondants à ces emails
            const emailElements = document.querySelectorAll(".email-item");
            emailElements.forEach(emailItem => {
                const rawSender = emailItem.querySelector("p:nth-child(3)") ? emailItem.querySelector("p:nth-child(3)").textContent.replace("📨 Expéditeur :", "").trim() : '';
            
                const senderMatch = rawSender.match(/^(.*?) - ([\w\.-]+@[\w\.-]+\.\w+)$/);
                let emailSender = senderMatch ? senderMatch[2].trim() : '';
                const emailSubject = emailItem.querySelector("p:nth-child(2)") ? emailItem.querySelector("p:nth-child(2)").textContent.trim() : ''
                console.log(emailSender === email.sender)
                if (emailSender === email.mail && emailSubject === email.subject) {
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

