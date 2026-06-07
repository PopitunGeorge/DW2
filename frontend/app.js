document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('app');

    const fetchData = async (endpoint) => {
        const response = await fetch(`http://127.0.0.1:8000/${endpoint}`);
        const data = await response.json();
        return data;
    };

    const renderData = (data, title) => {
        const card = document.createElement('div');
        card.classList.add('card');
        const heading = document.createElement('h2');
        heading.textContent = title;
        card.appendChild(heading);
        const content = document.createElement('pre');
        content.textContent = JSON.stringify(data, null, 2);
        card.appendChild(content);
        app.appendChild(card);
    };

    const init = async () => {
        const assets = await fetchData('assets');
        renderData(assets, 'Assets');

        const sources = await fetchData('sources');
        renderData(sources, 'Sources');

        const portfolios = await fetchData('portfolios');
        renderData(portfolios, 'Portfolios');
    };

    init();
});
