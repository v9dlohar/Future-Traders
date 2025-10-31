fetch('/get-optionchain-data/')
    .then(response => response.json())
    .then(json => {
        const container = document.getElementById('optionchain-container');
        const data = json.data;

        let html = '<table><tr>';
        for (let key in data[0]) {
            html += `<th>${key}</th>`;
        }
        html += '</tr>';

        data.forEach(row => {
            html += '<tr>';
            for (let key in row) {
                html += `<td>${row[key]}</td>`;
            }
            html += '</tr>';
        });

        html += '</table>';
        container.innerHTML = html;
    });
