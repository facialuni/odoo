$(document).ready(function() {

	setTimeout(function() {
		$('.app_name').on('click',function(event) {
			var settingName = $(event.currentTarget).attr('setting');
			$('.selected').removeClass('selected');
			$(event.currentTarget).addClass('selected');
			$('.show').addClass('o_hidden').removeClass('show');
			$('.' + settingName + '_setting_view').addClass('show').removeClass('o_hidden');
		});
	}, 2000);

});