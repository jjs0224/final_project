// Modal.jsx
export default function Modal({ isOpen, onClose, onConfirm, message }) {
  // isOpen이 false(닫힘 상태)면 아무것도 그리지 않음
  if (!isOpen) return null;

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <p>{message}</p>
        <div style={buttonGroupStyle}>
          <button onClick={onClose}>Cancel</button>
          <button onClick={onConfirm} style={confirmButtonStyle}>Confirm</button>
        </div>
      </div>
    </div>
  );
}

// 간단한 스타일 (실제로는 CSS 파일에 작성하는 것이 좋습니다)
const overlayStyle = {
  position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
  backgroundColor: 'rgba(0, 0, 0, 0.5)', display: 'flex', 
  justifyContent: 'center', alignItems: 'center', zIndex: 1000
};

const modalStyle = {
  backgroundColor: 'white', padding: '20px', borderRadius: '8px',
  textAlign: 'center', minWidth: '300px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
};

const buttonGroupStyle = { marginTop: '20px', display: 'flex', justifyContent: 'center', gap: '10px' };
const confirmButtonStyle = { backgroundColor: '#007bff', color: 'white', border: 'none', padding: '5px 15px', borderRadius: '4px', cursor: 'pointer' };