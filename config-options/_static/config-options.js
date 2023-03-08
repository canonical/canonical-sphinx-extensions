$(document).ready(function() {

    /* Hide all details except if the URL has an anchor for one */
    $('.configoption .details').addClass('hide-details');

    if ($(location).attr('hash')) {
        $('#'+$.escapeSelector($(location).attr('hash').substr(1))+" .details").removeClass('hide-details');
    };

    /* Make the option lines expandable */
    $('.configoption div.basicinfo').click(function() {
        $(this).nextAll('.configoption .details').first().toggleClass('hide-details');
    });

    /* When clicking a config reference, expand it automatically */
    $('.configref').click(function() {
        if ($(this).attr('href').substr(0,1) == "#") {
            $('.configoption .details').addClass('hide-details');
            $('#'+$.escapeSelector($(this).attr('href').substr(1))+" .details").removeClass('hide-details');
        };
    });

})
