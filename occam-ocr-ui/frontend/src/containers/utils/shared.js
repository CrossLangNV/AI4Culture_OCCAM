
// line with icon and text
export const IconText = ({ icon, text}) => {
  return (
          <div className="flex w-full relative align-items-center justify-content-start my-3 px-4">
        <div className="border-top-1 border-300 top-50 left-0 absolute w-full"></div>
        <div className="px-2 z-1 surface-0 flex align-items-center">
          <i className={`pi ${icon} text-900 mr-2`}></i>
          <span className="text-900 font-medium">{text}</span>
        </div>
      </div>
  )
}
