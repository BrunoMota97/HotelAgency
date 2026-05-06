const labels = JSON.parse('{{ labels | tojson | safe }}');
const chartData = JSON.parse('{{ data | tojson | safe }}');


const data = {
            labels: labels,
            datasets: [{
                label: 'Número de feedbacks por classificação (todos os quartos)',
                backgroundColor: 'rgb(36, 127, 191)',
                borderColor: 'rgb(36, 127, 191)',
                data: chartData,
            }]
        };


const config = {
            type: 'bar',
            data: data,
            options: { maintainAspectRatio: true }
        };

const myChart = new Chart(
            document.getElementById('myChart'),
            config
        );
