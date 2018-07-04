function proposalNavbarclickDataHref(d){
    if(d.classList.contains('active')){
        // if the navbar button is already active, remove filter, go to proposals page
        window.location.href = '/proposals'
    } else {
        window.location.href = d.getAttribute("data-href");
    }
}

function hideShow(element_id) {
    var x = document.getElementById(element_id);
    if (x.style.display === "none") {
        x.style.display = "block";
    } else {
        x.style.display = "none";
    }
}

function fix_anchors(){
    if(window.location.hash) {
        scrollBy(0, -150)
    }
}