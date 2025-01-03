new Vue({
    delimiters: ['[[', ']]'],
    el: "#app",
    data: {
        errorMessage: '',
        service: '',
        desc: '',
        price: ''
    },
    methods: {
        redirectToDashboard() {
            window.location.href = '/admin/dashboard';  
        },
        submitService() {
            fetch('/service_add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    service: this.service,
                    desc: this.desc,
                    price: this.price
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    sessionStorage.setItem("serviceAdded", data.message);
                    this.redirectToDashboard();
                } else {
                    this.errorMessage = data.message;
                }
            })
        }
    }
});
