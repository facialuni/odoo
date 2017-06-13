odoo.define('mail.DocumentViewer', function(require) {
    "use strict";

    var Widget = require('web.Widget');
    var core = require('web.core');
    var QWeb = core.qweb;

    var ZOOM_STEP = 0.5;
    var SCROLL_ZOOM_STEP = 0.1;

    var DocumentViewer = Widget.extend({
        template: "DocumentViewer",
        events: {
            'click .o_close_btn, .o_viewer_img_wrapper': '_onClose',
            'click .o_download_btn': '_onDownload',
            'click .o_viewer_img': '_onImageClick',
            'click .move_next': '_onNext',
            'click .move_previous': '_onPrevious',
            'click .o_zoom_in': '_onZoomIn',
            'click .o_zoom_out': '_onZoomOut',
            'DOMMouseScroll .o_viewer_content': '_onScroll',    // Firefox
            'mousewheel .o_viewer_content': '_onScroll',        // Chrome, Safari, IE
            'keydown': '_onKeydown',
            'mousedown .o_viewer_img': '_startDrag',
            'mousemove .o_viewer_content': '_doDrag',
            'mouseup .o_viewer_content': '_endDrag'
        },
        /**
         * When initialize document viewer get image and video type attachment from thread
         * and store it in instance so we can traversal attachment on next previous
         *
         * keep track of currently loaded attachment by 'active_attachment'
         *
         * @param {OdooWidget} thread
         */
        init: function (thread) {
            var attachment_ids = thread.get('attachment_ids');
            this.active_attachment = false;
            this.scale = 1;
            this.attachment_ids = _.filter(attachment_ids, function(attachment) {
                var type = attachment.mimetype.split('/').shift();
                if (type === 'image' || type === 'video') {
                    attachment.type = type;
                    return true;
                }
            });
        },
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * renderContent call after set 'active_attachment' to reflect change on DOM.
         * used after next, previous to display new content(image/video)
         */
        renderContent: function () {
            this.$('.o_viewer_content').html(QWeb.render('DocumentViewer.Content', {
                widget: this
            }));
            this.$('.o_viewer_img').load(_.bind(this._onImageLoaded, this));
            this._reset();
        },

        /**
         * Open popup/modal with given attachment_id
         * @param  {integer} attachment_id
         */
        on_attachment_popup: function (attachment_id) {
            this.active_attachment = _.findWhere(this.attachment_ids, {
                id: attachment_id
            });
            this.renderElement();
            this.$el.modal('show');
            this.$el.on('hidden.bs.modal', _.bind(this._onDestroy, this));
            this.$('.o_viewer_img').load(_.bind(this._onImageLoaded, this));
            this._reset();
        },

        //--------------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------------

        /**
         * Remove loading indicator when image loaded
         * @private
         */
        _onImageLoaded: function (){
            this.$('.o_loading_img').hide();
        },
        /**
         * Zoom in/out image by provided scale
         * @private
         * @param  {integer} scale
         */
        _onZoom: function (scale) {
            if (scale > 0.5){
                this.$('.o_viewer_img').css('transform', 'scale3d(' + scale + ', ' + scale + ', 1)');
                this.scale = scale;
            }
        },
        /**
         * When popup close complete destroyed modal even DOM footprint too
         * @private
         */
        _onDestroy: function () {
            if (this.isDestroyed()) {
                return;
            }
            this.$el.modal('hide');
            this.$el.remove();
        },
        /**
         * reset widget param used to reset widget on next previous move
         * @private
         */
        _reset: function(){
            this.scale = 1;
            this.dragStartX = this.dragstopX = 0;
            this.dragStartY = this.dragstopY = 0;
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} e
         */
        _onClose: function (e) {
            e.preventDefault();
            this.$el.modal('hide');
        },
        /**
         * @private
         * @param {MouseEvent} e
         */
        _onDownload: function (e) {
            e.preventDefault();
            window.location = '/web/content/' + this.active_attachment.id + '?download=true';
        },
        /**
         * On click of image do not close modal so stop event propagation
         * @private
         * @param {MouseEvent} e
         */
        _onImageClick: function (e) {
            e.stopPropagation();
        },
        /**
         * @private
         * @param {MouseEvent} e
         */
        _onNext: function (e) {
            e.preventDefault();
            var index = _.findIndex(this.attachment_ids, this.active_attachment);
            index = index + 1;
            index = index % this.attachment_ids.length;
            this.active_attachment = this.attachment_ids[index];
            this.renderContent();
        },
        /**
         * @private
         * @param {MouseEvent} e
         */
        _onPrevious: function (e) {
            e.preventDefault();
            var index = _.findIndex(this.attachment_ids, this.active_attachment);
            index = index === 0 ? this.attachment_ids.length - 1 : index - 1;
            this.active_attachment = this.attachment_ids[index];
            this.renderContent();
        },
        /**
         * @private
         * @param {MouseEvent} e
         */
        _onZoomIn: function (e) {
            e.preventDefault();
            var scale = this.scale + ZOOM_STEP;
            this._onZoom(scale);
        },
        /**
         * @private
         * @param {MouseEvent} e
         */
        _onZoomOut: function (e) {
            e.preventDefault();
            var scale = this.scale - ZOOM_STEP;
            this._onZoom(scale);
        },
        /**
         * @private
         * @param {MouseEvent} e
         */
        _startDrag: function (e) {
            e.preventDefault();
            this.enableDrag = true;
            this.dragStartX = e.clientX - (this.dragstopX || 0);
            this.dragStartY = e.clientY - (this.dragstopY || 0);
        },
        /**
         * @private
         * @param {MouseEvent} e
         */
        _doDrag: function (e) {
            e.preventDefault();
            if (this.enableDrag) {
                var $img = $('.o_viewer_img');
                var imgOffset = $img.offset();
                var left = imgOffset.left < 0 ? e.clientX - this.dragStartX : 0;
                var top = imgOffset.top < 0 ? e.clientY - this.dragStartY : 0;
                this.$('.o_viewer_img_wrapper')
                    .css("transform", "translate3d("+ left +"px, " + top + "px, 0)");
            }
        },
        /**
         * @private
         * @param {MouseEvent} e
         */
        _endDrag: function (e) {
            e.preventDefault();
            if (this.enableDrag) {
                this.enableDrag = false;
                this.dragstopX = e.clientX - this.dragStartX;
                this.dragstopY = e.clientY - this.dragStartY;
            }
        },
        /**
         * Zoom image on scroll
         * @private
         * @param {MouseEvent} e
         */
        _onScroll: function (e) {
            if (e.originalEvent.wheelDelta > 0 || e.originalEvent.detail < 0) {
                var scale = this.scale + SCROLL_ZOOM_STEP;
                this._onZoom(scale);
            } else {
                var scale = this.scale - SCROLL_ZOOM_STEP;
                this._onZoom(scale);
            }
        },
        /**
         * Move next previous attachment on keyboard right left key
         * @private
         * @param {KeyEvent} e
         */
        _onKeydown: function (e){
            switch (e.which) {
                case $.ui.keyCode.RIGHT:
                    this._onNext(e);
                    break;
                case $.ui.keyCode.LEFT:
                    this._onPrevious(e);
                    break;
            }
        },
    });
    return DocumentViewer;
});