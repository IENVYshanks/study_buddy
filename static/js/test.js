let form = document.getElementById("upload_file");

form.addEventListener("submit", async function(event) {
    event.preventDefault();  // 🔥 stop page reload

    let fileInput = document.querySelector('input[name="test_upload"]');
    let selectedFile = fileInput.files[0];

    if (!selectedFile) {
        console.log("No file selected");
        return;
    }

    let formData = new FormData();
    formData.append("test_input", selectedFile);

    try {
        let res = await fetch("/", {
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            throw new Error(`Server error: ${res.status}`);
        }

        let data = await res.json();
        console.log("Response:", data);

    } catch (err) {
        console.error("Error:", err);
    }
});

document.getElementById("deleteBtn").addEventListener("click", async () => {
    try {
        let res = await fetch("/delete_all", { method: "POST" });

        if (!res.ok) throw new Error(res.status);

        let data = await res.json();
        console.log("Delete Response:", data);

    } catch (err) {
        console.error(err);
    }
});

document.getElementById("authBtn").addEventListener("click", async () => {
    try {
        let token = localStorage.getItem("token");

        if (!token) {
            console.log("No token found");
            return;
        }

        let res = await fetch("/protected", {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (!res.ok) throw new Error(res.status);

        let data = await res.json();
        console.log("Protected Response:", data);

    } catch (err) {
        console.error(err);
    }
});

document.getElementById("createTokenBtn").addEventListener("click", async () => {
    try {
        let res = await fetch("/create_token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: "test_user",
                password: "test_password"
            })
        });

        if (!res.ok) throw new Error(res.status);

        let data = await res.json();
        localStorage.setItem("token", data.token);

        console.log("Token stored:", data.token);

    } catch (err) {
        console.error(err);
    }
});

document.getElementById("createRAG").addEventListener("click", async () =>{
    try{
        let res = await fetch ("/create_rag",{
            method : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: "test_user"
            })
        });
        let data = await res.json();
        console.log(data)

    }catch(err){
        console.log(err)
    }
});
    
