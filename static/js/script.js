document.addEventListener('DOMContentLoaded', () => {

    // Cek apakah kita berada di halaman yang memiliki tabel buku
    const bookTableBody = document.getElementById('book-table-body');
    if (!bookTableBody) return; // Keluar jika tidak ada tabel buku

    const searchInput = document.getElementById('search-input');
    const categoryFilter = document.getElementById('category-filter');
    const tableRows = Array.from(bookTableBody.getElementsByTagName('tr'));

    // --- Fungsi Filter dan Pencarian Gabungan ---
    const filterTable = () => {
        const searchTerm = searchInput.value.toLowerCase();
        const selectedCategory = categoryFilter.value.toLowerCase();

        tableRows.forEach(row => {
            const title = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
            const author = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
            const category = row.dataset.category || '';
            const status = row.querySelector('td:nth-child(6)').textContent.toLowerCase();

            // Pencarian sekarang mencakup judul, penulis, dan status
            const textMatch = title.includes(searchTerm) || author.includes(searchTerm) || status.includes(searchTerm);
            const categoryMatch = selectedCategory === 'all' || category === selectedCategory;

            if (textMatch && categoryMatch) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    };

    // --- Fungsi Pengurutan Tabel ---
    const sortHeaders = document.querySelectorAll('th[data-sort]');
    let sortDirection = {}; // Objek untuk menyimpan arah sort setiap kolom

    sortHeaders.forEach(header => {
        const sortKey = header.dataset.sort;
        sortDirection[sortKey] = 'asc'; // Default ascending

        header.addEventListener('click', () => {
            const currentDirection = sortDirection[sortKey];
            const newDirection = currentDirection === 'asc' ? 'desc' : 'asc';
            sortDirection[sortKey] = newDirection;

            // Reset ikon sort di semua header
            sortHeaders.forEach(h => h.querySelector('i').className = 'fas fa-sort');
            // Set ikon untuk header yang aktif
            header.querySelector('i').className = newDirection === 'asc' ? 'fas fa-sort-up' : 'fas fa-sort-down';

            // Lakukan pengurutan
            const sortedRows = tableRows.sort((a, b) => {
                const valA = a.querySelector(`td:nth-child(${header.cellIndex + 1})`).textContent.trim().toLowerCase();
                const valB = b.querySelector(`td:nth-child(${header.cellIndex + 1})`).textContent.trim().toLowerCase();

                if (valA < valB) return newDirection === 'asc' ? -1 : 1;
                if (valA > valB) return newDirection === 'asc' ? 1 : -1;
                return 0;
            });

            // Terapkan urutan baru ke tabel
            sortedRows.forEach(row => bookTableBody.appendChild(row));
        });
    });

    // --- Event Listeners & Inisialisasi ---
    searchInput.addEventListener('input', filterTable);
    categoryFilter.addEventListener('change', filterTable);

    // Cek parameter URL saat halaman dimuat
    const urlParams = new URLSearchParams(window.location.search);
    const statusFilter = urlParams.get('status');

    if (statusFilter) {
        searchInput.value = statusFilter;
        filterTable(); // Panggil filter setelah mengisi input
    }
});