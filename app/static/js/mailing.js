document.addEventListener("DOMContentLoaded", function () {
    fetchEmails(false);
    
    // ✅ Vérifier les nouveaux emails toutes les 10 secondes
    // setInterval(fetchEmails, 10000);  // 10000 ms = 10 secondes
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
    const opportunityFilterId = opportunityFilterElement ? opportunityFilterElement.value : 1;  

    const loading = document.getElementById("loading");
    if (loading) {
        loading.style.display = "block";
        emailContainer.style.display = "none";
        document.getElementById("searchContainer").style.display = "none";  
        document.getElementById("saveEmails").style.display = "none"; 
    }
    fetch(`/get_emails?mail_type_id=${opportunityFilterId}`, {
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
        console.log(data.emails)
        if (status === true) {
            updateEmailUI(data.emails_bdd, data.unread_count, data.emails_count,data.types);
        } else {
            updateEmailUI(data.emails, data.unread_count, data.emails_count,data.types);
        }
    })
    .catch(error => {
        console.error("🔴 Erreur :", error);
        alert("Erreur lors de la récupération des emails.");
    })
    .finally(() => {
        if (loading) {
            loading.style.display = "none";
            document.getElementById("emails").style.display = "flex";

            if (status === true) {
            } else {
                document.getElementById("searchContainer").style.display = "block";  
                document.getElementById("saveEmails").style.display = "block"; 
            }
        }
    });
}


// ✅ Fonction pour afficher les emails dans le dashboard
function updateEmailUI(emails, unread_count, emails_count, types) {
    const emailsList = document.getElementById("emails");
    emailsList.innerHTML = "";
    // 📩 Afficher les emails non lus
    if (emails.length > 0) {
        emails.forEach(mail => {
            const emailItem = document.createElement("div");
            emailItem.classList.add("email-item");
            emailItem.innerHTML = `
                <input type="checkbox" class="email-checkbox">
                <p><b>${mail.subject}</b></p>
                <p>📨 Expéditeur : ${mail.sender}</p>
                <p>📆 Reçu le : ${mail.receive_at}</p>
                <a href="${mail.path}" target="_blank">📩 Voir l'email</a>
                <p>📌 Probabilité : ${mail.percentage }</p>
                <p>📌 Type : ${mail.mail_type_id }</p>
            `;
            emailsList.appendChild(emailItem);
        });
        document.getElementById("opportunityFilter").addEventListener("change", filterEmails);
    } else {
        emailsList.innerHTML = "<p>Aucun email trouvé.</p>";
    }
    // ✅ Ajouter un événement pour filtrer les emails
    if (types) {
        const opportunityFilter = document.getElementById("opportunityFilter");

        // ✅ Ajouter les options dynamiquement
        types.forEach(mailType => {
            let option = document.createElement("option");
            option.value = mailType.id;
            option.textContent = mailType.type_name;
            opportunityFilter.appendChild(option);
        });
    }

    // 🔔 Mettre à jour les compteurs d'emails
    document.getElementById("unreadCount").textContent = unread_count;
    document.getElementById("mailCount").textContent = emails_count;
}

// ✅ Fonction pour filtrer les emails "Negoce Oui/Non"
function filterEmails() {
    const filterValue = document.getElementById("opportunityFilter").value;

    emails.forEach(email => {
        const negoceText = email.querySelector("p:last-child").textContent.trim();

        // 🔍 Debugging : Vérifier les valeurs réelles
        console.log("🔍 Filtrage en cours :", { filterValue, negoceText });

        // ✅ Appliquer le filtre correct
        if (filterValue === "all") {
            email.style.display = "block";  // ✅ Afficher tous les emails
        } else if (filterValue === "true" && negoceText.includes("Oui")) {
            email.style.display = "block";  // ✅ Afficher seulement "Negoce : Oui"
        } else if (filterValue === "false" && negoceText.includes("Non")) {
            email.style.display = "block";  // ✅ Afficher seulement "Negoce : Non"
        } else {
            email.style.display = "none";  // ❌ Cacher tous les autres emails
        }
    });
}


document.getElementById("saveEmails").addEventListener("click", function () {
    const selectedEmails = [];

    // 📩 Récupérer les emails cochés et enregistrer leurs détails
    document.querySelectorAll(".email-checkbox:checked").forEach(checkbox => {
        const emailItem = checkbox.closest(".email-item");
        
        const rawDate = emailItem.querySelector("p:nth-child(4)").textContent.trim();
        const cleanDate = rawDate.replace("📆 Reçu le :", "").trim();  

        const emailData = {
            subject: emailItem.querySelector("p:nth-child(2)").textContent.trim(),
            sender: emailItem.querySelector("p:nth-child(3)").textContent.replace("📨 Expéditeur :", "").trim(),
            receive_at: cleanDate,  // ✅ Utiliser la date propre
            path: emailItem.querySelector("a").getAttribute("href"),
            percentage: emailItem.querySelector("p:nth-child(6)").textContent.replace("📌 Probabilité :", "").trim(),
            type: emailItem.querySelector("p:nth-child(7)").textContent.replace("📌 Type :", "").trim()
        };

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
        location.reload();
    })
    .catch(error => {
        console.error("🔴 Erreur :", error);
        alert("Erreur lors de l'ajout des emails.");
    });
});

document.getElementById("searchForm").addEventListener("submit", function (event) {
    event.preventDefault(); 

    const searchCriteria = document.getElementById("searchCriteria").value.trim();
    const emailContainer = document.getElementById("emails");

    if (searchCriteria === "") {
        alert("Veuillez entrer un critère de recherche.");
        return;
    }

    fetch(`api/searchCriteria?criterion=${encodeURIComponent(searchCriteria)}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            emailContainer.innerHTML = `<p style="color:red;">❌ ${data.error}</p>`;
            return;
        }

        if (data.count === 0) {
            emailContainer.innerHTML = "<p>Aucun email trouvé.</p>";
            return;
        }

        let emailList = `<h3>📩 Résultats (${data.count}) - ${data.message}</h3>`;
        // data.emails.forEach(mail => {
        //     emailList += `
        //         <div class="email-item">
        //             <p><b>${mail.subject}</b> de ${mail.from}</p>
        //             <p>📆 Reçu le : ${mail.receive_at}</p>
        //             <p>📌 Negoce : ${mail.is_negoce ? "✅ Oui" : "❌ Non"}</p>
        //         </div>
        //     `;
        // });

        emailContainer.innerHTML = emailList;
    })
    .catch(error => {
        console.error("Erreur :", error);
        emailContainer.innerHTML = `<p style="color:red;">❌ Erreur de récupération des emails.</p>`;
    });
});

document.getElementById("messageIcon").addEventListener("click", function () {
    setTimeout(() => fetchEmails(false), 200); // ✅ Attendre 200ms pour s'assurer que l'élément est visible
});

document.getElementById("mailIcon").addEventListener("click", function () {
    setTimeout(() => fetchEmails(true), 200);
});

