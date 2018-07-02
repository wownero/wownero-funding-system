function clickDataHref(d){
    window.location.href = d.getAttribute("data-href");
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