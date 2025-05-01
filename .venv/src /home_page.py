import streamlit as st

def show_home_page():
    st.markdown('<h1 class="main-header">Smart ID Verification Portal</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Secure and Quick Identity Verification</p>', unsafe_allow_html=True)

    st.markdown("""
    <div style="background-color: #f0f7ff; padding: 20px; border-radius: 10px; margin-bottom: 30px;">
        <p style="font-size: 16px; color: #333;">Complete your identity verification process in just a few steps. We ensure a secure and streamlined 
        experience for all our customers.</p>
        <p style="font-weight: bold; color: #1E88E5;">Estimated completion time: 5-7 minutes</p>
    </div>
    """, unsafe_allow_html=True)

    # Icon-based steps in a row with colored backgrounds
    st.markdown("""
    <div style="display: flex; flex-direction: row; justify-content: space-between; margin: 30px 0;">
        <div style="text-align: center; flex: 1; max-width: 120px;">
            <div style="width: 60px; height: 60px; background-color: #2196F3; border-radius: 8px; margin: 0 auto; display: flex; justify-content: center; align-items: center;">
                <span style="font-size: 28px; color: white;">📄</span>
            </div>
            <div style="font-size: 14px; color: #424242; margin-top: 10px; font-weight: 500;">Document Upload</div>
        </div>
        <div style="text-align: center; flex: 1; max-width: 120px;">
            <div style="width: 60px; height: 60px; background-color: #673AB7; border-radius: 8px; margin: 0 auto; display: flex; justify-content: center; align-items: center;">
                <span style="font-size: 28px; color: white;">📷</span>
            </div>
            <div style="font-size: 14px; color: #424242; margin-top: 10px; font-weight: 500;">Face Recognition</div>
        </div>
        <div style="text-align: center; flex: 1; max-width: 120px;">
            <div style="width: 60px; height: 60px; background-color: #4CAF50; border-radius: 8px; margin: 0 auto; display: flex; justify-content: center; align-items: center;">
                <span style="font-size: 28px; color: white;">🕒</span>
            </div>
            <div style="font-size: 14px; color: #424242; margin-top: 10px; font-weight: 500;">Identity Verification</div>
        </div>
        <div style="text-align: center; flex: 1; max-width: 120px;">
            <div style="width: 60px; height: 60px; background-color: #26A69A; border-radius: 8px; margin: 0 auto; display: flex; justify-content: center; align-items: center;">
                <span style="font-size: 28px; color: white;">✅</span>
            </div>
            <div style="font-size: 14px; color: #424242; margin-top: 10px; font-weight: 500;">Final Confirmation</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Start onboarding button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Start Onboarding", key="start_onboarding", use_container_width=True):
        st.session_state.page = 'document_upload'
        st.rerun()

    # Security information section
    st.markdown("""
    <div style="background-color: #E3F2FD; padding: 20px; border-radius: 10px; margin: 30px 0;">
        <h3 style="color: #1E88E5; margin-top: 0;">🔒 Security Information</h3>
        <ul style="list-style-type: none; padding-left: 0;">
            <!--<li style="margin: 10px 0; display: flex; align-items: center;">
                <span style="color: #4CAF50; margin-right: 10px;">✓</span> Your data is encrypted and secure
            </li> -->
            <li style="margin: 10px 0; display: flex; align-items: center;">
                <span style="color: #4CAF50; margin-right: 10px;">✓</span> Process takes approximately 5-7 minutes
            </li>
            <li style="margin: 10px 0; display: flex; align-items: center;">
                <span style="color: #4CAF50; margin-right: 10px;">✓</span> Requires webcam/camera access
            </li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #757575;">
        <p>Need help? Contact our support team at <a href="mailto:support@company.com">support@company.com</a></p>
        <p>© 2025 Smart ID Verification. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)
